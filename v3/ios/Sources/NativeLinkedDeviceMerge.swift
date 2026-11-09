import Foundation

/// A local, manual owner-directed merge. This has NO cloud adapter, account
/// connection, network operation or implicit link to another anonymous person.
enum NativeLinkedDeviceMergeError: LocalizedError, Equatable {
    case unlinkedIdentity
    case incompleteHistory
    case missingRegion
    case conflictingEvents
    case incompatibleProgress
    case invalidSource

    var errorDescription: String? {
        switch self {
        case .unlinkedIdentity:
            return "These exports are different anonymous learners. First transfer one profile using the confirmed Restore action; do not combine their XP."
        case .incompleteHistory:
            return "This learning history predates the complete attempt journal. It cannot be merged without inventing old attempts."
        case .missingRegion:
            return "An older practice reward does not contain its original Poland region. A complete map cannot be reconciled."
        case .conflictingEvents:
            return "The same practice event has different details on the two devices. Neither history was changed."
        case .incompatibleProgress:
            return "The saved progress and the verified event journal do not agree."
        case .invalidSource:
            return "The proposed linked-device progress failed source verification."
        }
    }
}

struct NativeLinkedDevicePlan {
    let candidate: LocalLearner
    let originalEventCount: Int
    let incomingEventCount: Int
    let mergedEventCount: Int
    let mergedEffortXP: Int
    let mergedRegionXP: Int

    var newEvents: Int { mergedEventCount - originalEventCount }
}

/// Pure projection only. The LocalLearningStore must re-check both source
/// archive and on-disk current profile, write a protected backup, then persist
/// this complete value atomically. It must NEVER mutate live profile itself.
enum NativeLinkedDeviceMerge {
    static func propose(local: LocalLearner, incoming: LocalLearner,
                        lessons: [Lesson], regions: [PolandRegion])
        throws -> NativeLinkedDevicePlan {
        guard local.localID == incoming.localID,
              local.firstOpened == incoming.firstOpened,
              local.localID != UUID(uuidString: "00000000-0000-0000-0000-000000000000")! else {
            throw NativeLinkedDeviceMergeError.unlinkedIdentity
        }
        guard let a = local.practiceJournal,
              let b = incoming.practiceJournal else {
            throw NativeLinkedDeviceMergeError.incompleteHistory
        }
        guard !a.hasLegacyHistory && !b.hasLegacyHistory else {
            throw NativeLinkedDeviceMergeError.incompleteHistory
        }
        do {
            try a.validateSource(lessons: lessons, regions: regions)
            try b.validateSource(lessons: lessons, regions: regions)
        } catch {
            throw NativeLinkedDeviceMergeError.invalidSource
        }
        let combined: NativePracticeJournal
        do {
            combined = try NativePracticeJournal.mergeCandidate(a, b, lessons: lessons)
        } catch NativePracticeJournalError.conflictingEvent {
            throw NativeLinkedDeviceMergeError.conflictingEvents
        } catch NativePracticeJournalError.unlinkedOrLegacy {
            throw NativeLinkedDeviceMergeError.unlinkedIdentity
        } catch {
            throw NativeLinkedDeviceMergeError.invalidSource
        }

        let records: [String: PracticeRecord]
        let projected: NativeXPReconciliationCandidate
        do {
            records = try combined.projectedRecords(lessons: lessons)
            projected = try NativeXPReconciliation.candidate(journal: combined, lessons: lessons)
        } catch {
            throw NativeLinkedDeviceMergeError.invalidSource
        }
        let regionProjection: NativeProjectedRegionLedger
        do {
            regionProjection = try projected.projectedRegions(verifiedSourceRegions: regions)
        } catch NativeRegionProjectionError.missingHistoricalRegion {
            throw NativeLinkedDeviceMergeError.missingRegion
        } catch {
            throw NativeLinkedDeviceMergeError.invalidSource
        }
        let mapRegion = (local.expedition ?? LocalExpedition()).selectedRegion
        guard regions.contains(where: { $0.id == mapRegion }) else {
            throw NativeLinkedDeviceMergeError.invalidSource
        }
        // Rebuild from original source events, never sum device-local daily XP
        // balances. Award identity is stable item + mode + Gregorian UTC date.
        let events: [LocalXPEvent] = try projected.awards.map { award in
            guard let region = award.regionID else {
                throw NativeLinkedDeviceMergeError.missingRegion
            }
            let key = award.mode.rawValue + ":" + award.itemID + ":" + award.utcDay
            return LocalXPEvent(id: key, itemID: award.itemID, mode: award.mode,
                                at: award.at, xp: award.effortXP,
                                baseXP: award.effortXP,
                                expeditionXP: award.expeditionXP,
                                tier: award.tier, regionID: region)
        }
        guard events.count <= 20_000,
              Set(events.map(\.id)).count == events.count,
              events.reduce(0, { $0 + $1.xp }) == projected.totalEffortXP,
              events.reduce(0, { $0 + $1.expeditionXP }) == projected.totalExpeditionXP else {
            throw NativeLinkedDeviceMergeError.incompatibleProgress
        }

        var result = local
        result.records = records
        result.practiceJournal = combined
        result.linkedUTCEpoch = combined.epochID
        result.expedition = LocalExpedition(selectedRegion: mapRegion,
                                           regionGoals: regionProjection.goals,
                                           events: events)
        // Local UI navigation, current region, tourist completion and guided
        // cursor remain on this device. The other phone's actor ID is ignored.
        return NativeLinkedDevicePlan(
            candidate: result,
            originalEventCount: a.events.count,
            incomingEventCount: b.events.count,
            mergedEventCount: combined.events.count,
            mergedEffortXP: projected.totalEffortXP,
            mergedRegionXP: projected.totalExpeditionXP)
    }
}
