import Foundation

/// A READ-ONLY, source-verified decision about what an explicitly approved
/// private CloudKit operation may do next. It does not contact iCloud, merge
/// histories, mutate XP, or persist progress.
enum NativeCloudSyncDecision: Equatable {
    case create
    case uploadLocalAdditions(count: Int)
    case alreadyCurrent
    case reviewRemoteAdditions(count: Int)
}

enum NativeCloudSyncPlanner {
    /// The only safe auto-upload is when every existing remote event is
    /// already in the local source-verified journal, byte-identical by UUID.
    /// Unseen remote answers must be imported and REVIEWED by the owner,
    /// not silently overwritten by a last-writer-wins profile.
    static func decide(local learner: LocalLearner,
                       scope: NativePrivateCloudScope,
                       remote: NativeCloudKitEnvelope?,
                       knownGeneration: UInt64,
                       lessons: [Lesson],
                       regions: [PolandRegion]) throws -> NativeCloudSyncDecision {
        guard learner.localID == scope.learnerID,
              learner.linkedUTCEpoch == scope.journalEpoch,
              let journal = learner.practiceJournal,
              journal.epochID == scope.journalEpoch,
              !journal.hasLegacyHistory else {
            throw NativeCloudKitError.unsupportedHistory
        }
        let proposed = NativeCloudKitEnvelope(
            scope: scope, generation: 1, deleted: false, journal: journal)
        try proposed.validate(lessons: lessons, regions: regions)

        guard let remote else {
            // If this phone has ever seen a server revision, a missing
            // record/zone is NOT permission to recreate deleted history.
            guard knownGeneration == 0 else {
                throw NativeCloudKitError.staleChangeTag
            }
            return .create
        }
        guard remote.scope == scope else {
            throw NativeCloudKitError.foreignLearner
        }
        try remote.validate(lessons: lessons, regions: regions)
        guard remote.generation >= knownGeneration else {
            throw NativeCloudKitError.staleChangeTag
        }
        guard !remote.deleted else { throw NativeCloudKitError.deleted }
        guard let remoteJournal = remote.journal else {
            throw NativeCloudKitError.incompatibleRecord
        }

        let merged: NativePracticeJournal
        do {
            merged = try NativePracticeJournal.mergeCandidate(
                remoteJournal, journal, lessons: lessons)
        } catch {
            // A same-ID payload conflict also requires owner/diagnostic
            // recovery, never a silent CloudKit write or chosen winner.
            throw NativeCloudKitError.remoteAhead
        }
        let remoteIds = Set(remoteJournal.events.map(\.id))
        let localIds = Set(journal.events.map(\.id))
        guard merged.events.count >= remoteJournal.events.count,
              merged.events.count >= journal.events.count else {
            throw NativeCloudKitError.incompatibleRecord
        }
        if !remoteIds.isSubset(of: localIds) {
            return .reviewRemoteAdditions(count: remoteIds.subtracting(localIds).count)
        }
        if localIds == remoteIds { return .alreadyCurrent }
        return .uploadLocalAdditions(count: localIds.subtracting(remoteIds).count)
    }
}
