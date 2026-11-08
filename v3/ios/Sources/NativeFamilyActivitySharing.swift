import Foundation

/// A consented family contribution has no relationship to local XP totals.
/// The private V2 server decides XP, repeat taper, UTC day and membership.
/// The candidate list is ephemeral and deliberately excludes pre-login history.
enum NativeFamilyActivityReceipt: Equatable {
    case credited(xp: Int, expeditionXP: Int)
    case alreadyCredited
}

struct NativeFamilyActivityReply: Decodable {
    let accepted: Bool
    let reason: String?
    let xp: Int?
    let expedition_xp: Int?
    let region: String?
    let target: Int?
}

enum NativeFamilyActivityGuard {
    static func dayUTC(_ at: Date) -> DateComponents {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar.dateComponents([.year, .month, .day], from: at)
    }

    /// No historical replay when a learner later connects an account.
    /// Same current UTC day as the V2 server and at/after voluntary sign-in.
    /// The server retains authority to accept or reject any contribution.
    static func candidates(events: [LocalXPEvent], lessons: [Lesson],
                           regions: [PolandRegion], connectedAt: Date,
                           now: Date = Date()) -> [LocalXPEvent] {
        guard now >= connectedAt else { return [] }
        let knownItems = Set(lessons.flatMap(\.items).map(\.id))
        let knownRegions = Set(regions.map(\.id))
        let currentDay = dayUTC(now)
        return events.filter { event in
            event.at >= connectedAt && event.at <= now &&
            dayUTC(event.at) == currentDay &&
            knownItems.contains(event.itemID) &&
            knownRegions.contains(event.regionID) &&
            (1...5).contains(event.tier) &&
            event.xp > 0 && event.xp == event.baseXP &&
            event.expeditionXP >= 0 && event.expeditionXP <= event.xp
        }
        .sorted { $0.at > $1.at }
        .prefix(20)
        .map { $0 }
    }

    static func receipt(_ data: Data, source: LocalXPEvent) throws -> NativeFamilyActivityReceipt {
        guard let reply = try? JSONDecoder().decode(NativeFamilyActivityReply.self, from: data) else {
            throw NativeFamilyError.malformedResponse
        }
        if !reply.accepted && reply.reason == "already_credited" &&
            reply.xp == nil && reply.expedition_xp == nil {
            return .alreadyCredited
        }
        guard reply.accepted, reply.reason == nil,
              let xp = reply.xp,
              [10, 14, 19, 26, 35].contains(xp),
              let mapXP = reply.expedition_xp, mapXP >= 0, mapXP <= xp,
              reply.region == source.regionID,
              let target = reply.target, target > 0 else {
            throw NativeFamilyError.malformedResponse
        }
        return .credited(xp: xp, expeditionXP: mapXP)
    }
}
