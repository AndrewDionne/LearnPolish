import Foundation
import CloudKit

/// Native CloudKit private-database transport, deliberately *not* connected
/// to first launch, AppShell, or an app entitlement. It may only be created
/// by a future user-approved, signed CloudKit capability.
enum NativeCloudKitError: LocalizedError, Equatable {
    case notAuthenticated
    case wrongAccount
    case foreignLearner
    case incompatibleRecord
    case unsupportedHistory
    case oversizedJournal
    case remoteAhead
    case staleChangeTag
    case deleted
    case invalidAcknowledgement

    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "A signed-in private iCloud account is required for optional synchronization."
        case .wrongAccount:
            return "iCloud account changed. The existing private history must not be accessed."
        case .foreignLearner:
            return "Private iCloud history does not belong to this anonymous learner."
        case .incompatibleRecord:
            return "The remote private record is incompatible; neither copy was overwritten."
        case .unsupportedHistory:
            return "Only complete, original-source-verified journal histories can be synchronized."
        case .oversizedJournal:
            return "Practice history exceeds the current single-record CloudKit limit. Nothing was uploaded."
        case .remoteAhead:
            return "Another phone has newer practice. Review and combine the histories before uploading."
        case .staleChangeTag:
            return "The remote record changed during synchronization. No replacement was made."
        case .deleted:
            return "Private cloud history was deleted. Stale devices cannot recreate it."
        case .invalidAcknowledgement:
            return "CloudKit did not confirm the expected private record; no success was recorded."
        }
    }
}

/// The single remote source-of-truth record holds either a verified full
/// journal OR a retained deletion tombstone. It never contains aggregate XP,
/// family memberships, a server token, provider recordings or transcripts.
/// A tombstone is *saved*, never hard-deleted, so stale clients cannot
/// trivially recreate a removed record.
struct NativeCloudKitEnvelope: Codable {
    static let format = "path-to-polish-private-journal"
    static let version = 1
    static let maximumBytes = 450_000

    let formatID: String
    let version: Int
    let scope: NativePrivateCloudScope
    let generation: UInt64
    let deleted: Bool
    let journal: NativePracticeJournal?

    init(scope: NativePrivateCloudScope, generation: UInt64,
         deleted: Bool, journal: NativePracticeJournal?) {
        formatID = Self.format
        version = Self.version
        self.scope = scope
        self.generation = generation
        self.deleted = deleted
        self.journal = journal
    }

    func validate(lessons: [Lesson], regions: [PolandRegion]) throws {
        guard formatID == Self.format, version == Self.version,
              generation > 0 else { throw NativeCloudKitError.incompatibleRecord }
        if deleted {
            guard journal == nil else { throw NativeCloudKitError.incompatibleRecord }
            return
        }
        guard let journal,
              journal.epochID == scope.journalEpoch,
              !journal.hasLegacyHistory else {
            throw NativeCloudKitError.unsupportedHistory
        }
        do {
            try journal.validateSource(lessons: lessons, regions: regions)
            let candidate = try NativeXPReconciliation.candidate(
                journal: journal, lessons: lessons)
            _ = try candidate.projectedRegions(verifiedSourceRegions: regions)
        } catch {
            throw NativeCloudKitError.unsupportedHistory
        }
    }

    func encoded(lessons: [Lesson], regions: [PolandRegion]) throws -> Data {
        try validate(lessons: lessons, regions: regions)
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(self)
        guard data.count <= Self.maximumBytes else {
            throw NativeCloudKitError.oversizedJournal
        }
        return data
    }

    static func decode(_ data: Data, lessons: [Lesson],
                       regions: [PolandRegion]) throws -> Self {
        guard !data.isEmpty, data.count <= maximumBytes else {
            throw NativeCloudKitError.oversizedJournal
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let envelope = try decoder.decode(Self.self, from: data)
        try envelope.validate(lessons: lessons, regions: regions)
        return envelope
    }
}

struct NativeCloudKitRemoteCopy {
    let envelope: NativeCloudKitEnvelope
    /// The *server* record's change tag, not an app-computed revision.
    let changeTag: String
}

/// The iOS 17 CloudKit APIs are compiled in unsigned Simulator CI, but no
/// iCloud capability, CKSyncEngine, background scheduling or feature UI is
/// enabled. All network operations require an explicit caller and verified
/// iCloud account on the exact request.
@MainActor
final class NativeCloudKitPrivateTransport {
    private let container: CKContainer
    private let database: CKDatabase
    private let zoneID = CKRecordZone.ID(zoneName: "PathToPolishPrivateV3",
                                         ownerName: CKCurrentUserDefaultName)
    private let recordType = "PathToPolishJournalV1"

    init(container: CKContainer = .default()) {
        self.container = container
        database = container.privateCloudDatabase
    }

    /// Called *only after* the user explicitly chooses private sync.
    /// CloudKit's opaque user-record ID is account continuity information,
    /// not an email address or a verified guardian identity.
    func authenticatedAccountKey() async throws -> String {
        guard try await container.accountStatus() == .available else {
            throw NativeCloudKitError.notAuthenticated
        }
        let name = try await container.userRecordID().recordName
        guard (8...200).contains(name.count), !name.contains("@"),
              !name.contains(" ") else {
            throw NativeCloudKitError.notAuthenticated
        }
        return name
    }

    private func confirm(_ scope: NativePrivateCloudScope) async throws {
        guard try await authenticatedAccountKey() == scope.accountKey else {
            throw NativeCloudKitError.wrongAccount
        }
    }

    private func recordID(_ scope: NativePrivateCloudScope) -> CKRecord.ID {
        // Every anonymous learner+epoch gets a stable well-known record.
        // Never reuse a deleted ID for another learner.
        CKRecord.ID(recordName: "journal-" + scope.learnerID.uuidString +
                    "-" + scope.journalEpoch.uuidString, zoneID: zoneID)
    }

    private func parse(_ record: CKRecord,
                       scope: NativePrivateCloudScope,
                       lessons: [Lesson], regions: [PolandRegion])
        throws -> NativeCloudKitRemoteCopy {
        guard record.recordType == recordType,
              let tag = record.recordChangeTag, !tag.isEmpty,
              let data = record["payload"] as? Data else {
            throw NativeCloudKitError.incompatibleRecord
        }
        let envelope = try NativeCloudKitEnvelope.decode(
            data, lessons: lessons, regions: regions)
        guard envelope.scope == scope else {
            throw NativeCloudKitError.foreignLearner
        }
        return NativeCloudKitRemoteCopy(envelope: envelope, changeTag: tag)
    }

    private func readVerified(
        scope: NativePrivateCloudScope,
        lessons: [Lesson], regions: [PolandRegion]
    ) async throws -> (copy: NativeCloudKitRemoteCopy, record: CKRecord)? {
        try await confirm(scope)
        do {
            let record = try await database.record(for: recordID(scope))
            return (try parse(record, scope: scope,
                              lessons: lessons, regions: regions), record)
        } catch let error as CKError where error.code == .unknownItem {
            return nil
        }
    }

    /// User-initiated private read. The persisted, separately approved
    /// policy and anonymous learner identity are checked BEFORE *any*
    /// CloudKit network request, including reads. A tombstone found on this
    /// device is durably recorded before reporting deletion to the UI.
    func readManually(learner: LocalLearner,
                      gateStore: NativePrivateCloudGateStore,
                      lessons: [Lesson], regions: [PolandRegion])
        async throws -> NativeCloudKitRemoteCopy? {
        guard let scope = gateStore.gate.scope else {
            throw NativePrivateCloudGateError.explicitConsentRequired
        }
        let account = try await authenticatedAccountKey()
        try gateStore.gate.authorizeRemoteOperation(
            verifiedOpaqueAccountKey: account, learner: learner,
            snapshot: NativePrivateCloudSnapshot(
                scope: scope, generation: gateStore.gate.knownGeneration))
        let found = try await readVerified(
            scope: scope, lessons: lessons, regions: regions)?.copy
        guard try await authenticatedAccountKey() == scope.accountKey else {
            throw NativeCloudKitError.wrongAccount
        }
        if let found {
            if found.envelope.deleted {
                try gateStore.commit { try $0.observeVerifiedServerDeletion(
                    NativePrivateCloudTombstone(
                        scope: scope, generation: found.envelope.generation))
                }
                throw NativeCloudKitError.deleted
            }
            try gateStore.gate.authorizeRemoteOperation(
                verifiedOpaqueAccountKey: account, learner: learner,
                snapshot: NativePrivateCloudSnapshot(
                    scope: scope, generation: found.envelope.generation))
            try gateStore.commit { try $0.observeVerifiedServerRevision(
                NativePrivateCloudSnapshot(
                    scope: scope, generation: found.envelope.generation))
            }
        } else if gateStore.gate.knownGeneration != 0 {
            // Missing record after a previously verified generation must
            // not be treated as a fresh learner or recreated implicitly.
            throw NativeCloudKitError.staleChangeTag
        }
        return found
    }

    /// CloudKit's ifServerRecordUnchanged CAS rejects a stale change tag,
    /// including another device publishing a newer tombstone. No allKeys or
    /// changedKeys overwrite mode is permitted.
    private func compareAndSwap(_ envelope: NativeCloudKitEnvelope,
                                expected: NativeCloudKitRemoteCopy?,
                                lessons: [Lesson], regions: [PolandRegion])
        async throws -> NativeCloudKitRemoteCopy {
        let payload = try envelope.encoded(lessons: lessons, regions: regions)
        let current = try await readVerified(
            scope: envelope.scope, lessons: lessons, regions: regions)
        guard current?.copy.changeTag == expected?.changeTag else {
            throw NativeCloudKitError.staleChangeTag
        }
        let record: CKRecord
        if let current {
            record = current.record
        } else {
            // Only an explicit first write creates the private zone.
            // A deleted record is NEVER hard-deleted by this application.
            _ = try await database.save(CKRecordZone(zoneID: zoneID))
            record = CKRecord(recordType: recordType,
                              recordID: recordID(envelope.scope))
        }
        record["payload"] = payload as NSData
        // The real remote change tag is rechecked by the server even if it
        // changes after our read; do not silently retry on conflict.
        let result: (saveResults: [CKRecord.ID: Result<CKRecord, Error>],
                     deleteResults: [CKRecord.ID: Result<Void, Error>])
        do {
            result = try await database.modifyRecords(
                saving: [record], deleting: [],
                savePolicy: .ifServerRecordUnchanged, atomically: true)
        } catch let error as CKError where error.code == .serverRecordChanged {
            throw NativeCloudKitError.staleChangeTag
        }
        guard let returned = result.saveResults[record.recordID] else {
            throw NativeCloudKitError.invalidAcknowledgement
        }
        let saved: CKRecord
        do {
            saved = try returned.get()
        } catch let error as CKError where error.code == .serverRecordChanged {
            throw NativeCloudKitError.staleChangeTag
        }
        let acknowledgement = try parse(saved, scope: envelope.scope,
                                        lessons: lessons, regions: regions)
        guard acknowledgement.envelope.generation == envelope.generation,
              acknowledgement.envelope.deleted == envelope.deleted else {
            throw NativeCloudKitError.invalidAcknowledgement
        }
        return acknowledgement
    }

    /// Explicit manual upload only. This will NOT overwrite remote attempts:
    /// the server journal must be a verified subset of the local journal.
    /// The caller must first manually review a local two-device merge if
    /// the server has unseen events. Every remote request validates the
    /// actual Apple account before and after the network operation.
    func uploadManually(learner: LocalLearner,
                        gateStore: NativePrivateCloudGateStore,
                        lessons: [Lesson], regions: [PolandRegion])
        async throws -> NativeCloudKitRemoteCopy {
        guard let scope = gateStore.gate.scope,
              let journal = learner.practiceJournal,
              !journal.hasLegacyHistory,
              learner.linkedUTCEpoch == journal.epochID else {
            throw NativeCloudKitError.unsupportedHistory
        }
        // readManually enforces durable consent, account, generation and
        // remotely-deleted history before performing the network read.
        let current = try await readManually(
            learner: learner, gateStore: gateStore,
            lessons: lessons, regions: regions)
        let account = try await authenticatedAccountKey()
        let decision = try NativeCloudSyncPlanner.decide(
            local: learner, scope: scope, remote: current?.envelope,
            knownGeneration: gateStore.gate.knownGeneration,
            lessons: lessons, regions: regions)
        switch decision {
        case .reviewRemoteAdditions:
            throw NativeCloudKitError.remoteAhead
        case .alreadyCurrent:
            guard let current else { throw NativeCloudKitError.invalidAcknowledgement }
            return current
        case .create, .uploadLocalAdditions:
            break
        }
        // Account might have changed while remote was being fetched.
        guard try await authenticatedAccountKey() == account else {
            throw NativeCloudKitError.wrongAccount
        }
        let oldRevision = current?.envelope.generation ?? 0
        guard oldRevision < UInt64.max else {
            throw NativeCloudKitError.staleChangeTag
        }
        let envelope = NativeCloudKitEnvelope(
            scope: scope, generation: oldRevision + 1,
            deleted: false, journal: journal)
        let saved = try await compareAndSwap(
            envelope, expected: current, lessons: lessons, regions: regions)
        guard try await authenticatedAccountKey() == scope.accountKey else {
            throw NativeCloudKitError.wrongAccount
        }
        try gateStore.commit {
            try $0.observeVerifiedServerRevision(NativePrivateCloudSnapshot(
                scope: scope, generation: saved.envelope.generation))
        }
        return saved
    }

    /// Persist a *server-side* tombstone in the SAME record via CAS. Do not
    /// delete its record or zone: retaining the tombstone is the mechanism
    /// preventing an older phone from re-creating the history after deletion.
    func publishPendingDeletion(gateStore: NativePrivateCloudGateStore,
                                lessons: [Lesson], regions: [PolandRegion])
        async throws -> NativePrivateCloudTombstone {
        guard gateStore.gate.phase == .deletionPending,
              let request = gateStore.gate.requestedTombstone else {
            throw NativePrivateCloudGateError.invalidTransition
        }
        try await confirm(request.scope)
        // A pre-authorized pending-delete operation is the sole exception
        // to ordinary active-session reads. It must remain possible to
        // recover an acknowledged tombstone after an interrupted request.
        let current = try await readVerified(scope: request.scope,
                                             lessons: lessons, regions: regions)?.copy
        if let current, current.envelope.deleted {
            // Idempotent retry only after reading a real server tombstone.
            guard current.envelope.generation >= request.generation else {
                throw NativeCloudKitError.staleChangeTag
            }
            let acknowledged = NativePrivateCloudTombstone(
                scope: request.scope, generation: current.envelope.generation)
            try gateStore.commit {
                try $0.acknowledgeServerTombstone(acknowledged)
            }
            return acknowledged
        }
        guard (current?.envelope.generation ?? 0) + 1 ==
              request.generation else {
            // Never invent a new revision or bypass the pending gate.
            throw NativeCloudKitError.staleChangeTag
        }
        let tombstone = NativeCloudKitEnvelope(
            scope: request.scope, generation: request.generation,
            deleted: true, journal: nil)
        let saved = try await compareAndSwap(
            tombstone, expected: current, lessons: lessons, regions: regions)
        try await confirm(request.scope)
        let verified = NativePrivateCloudTombstone(
            scope: request.scope, generation: saved.envelope.generation)
        try gateStore.commit { try $0.acknowledgeServerTombstone(verified) }
        return verified
    }
}
