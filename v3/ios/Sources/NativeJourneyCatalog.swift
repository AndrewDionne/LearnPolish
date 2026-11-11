import Foundation

/// Small, navigable groups of the existing V2 source-ordered placements.
/// A group is a UI collection, not a newly-authored lesson or prerequisite.
/// Source lesson IDs and assessment records remain unchanged.
struct NativeJourneyCollection: Identifiable {
    let id: String
    let title: String
    let subtitle: String
    let lessons: [Lesson]
}

struct NativeJourneySnapshot {
    let startedLessons: Int
    let practisedLessons: Int
    let totalLessons: Int
    let recallCorrect: Int
    let recallAttempts: Int

    var recallPercentage: Int? {
        guard recallAttempts > 0 else { return nil }
        return Int((100.0 * Double(recallCorrect) / Double(recallAttempts)).rounded())
    }
}

enum NativeJourneyCatalog {
    static func collections(course: [Lesson],
                            placements: [String: JourneyPlacement]) -> [NativeJourneyCollection] {
        // Keep the actual source order, partition only at authored
        // Journey/position boundaries, then split into <=4 lessons.
        // The split does NOT assert the chapters are pedagogically certified.
        var result: [NativeJourneyCollection] = []
        for journey in 1...3 {
            for position in ["beginning", "middle", "end"] {
                let bucket = course.filter {
                    let p = placements[$0.id]
                    return p?.journey == journey && p?.position == position
                }
                guard !bucket.isEmpty else { continue }
                let numberOfParts = (bucket.count + 3) / 4
                for part in 0..<numberOfParts {
                    let start = part * 4
                    let set = Array(bucket[start..<min(start + 4, bucket.count)])
                    let suffix = numberOfParts > 1 ? " \(part + 1)" : ""
                    let heading: String
                    if journey == 1 {
                        switch position {
                        case "beginning": heading = part == 0 ? "First steps" : "Building foundations"
                        case "middle": heading = part == 0 ? "Everyday essentials" : "Everyday situations"
                        default: heading = "Conversations and understanding"
                        }
                    } else {
                        heading = "Journey \(journey) · \(position.capitalized)"
                    }
                    result.append(NativeJourneyCollection(
                        id: "journey-\(journey)-\(position)-\(part)",
                        title: heading + (part >= 2 ? suffix : ""),
                        subtitle: "Journey \(journey) · \(set.count) lessons",
                        lessons: set))
                }
            }
        }
        return result
    }

    /// Observed progress and recall, never a fabricated pronunciation score.
    /// "Practised" means at least one real saved attempt for every item
    /// (not mastery or independent linguistic accreditation).
    static func snapshot(_ collection: NativeJourneyCollection,
                         records: [String: PracticeRecord]) -> NativeJourneySnapshot {
        var started = 0
        var practised = 0
        var correct = 0
        var total = 0
        for lesson in collection.lessons {
            let actualCounts = lesson.items.map { item in
                PracticeMode.allCases.reduce(0) {
                    $0 + (records[$1.rawValue + ":" + item.id]?.attempts ?? 0)
                }
            }
            if actualCounts.contains(where: { $0 > 0 }) { started += 1 }
            if !actualCounts.isEmpty && actualCounts.allSatisfy({ $0 > 0 }) {
                practised += 1
            }
            for item in lesson.items {
                if let record = records["learn:" + item.id] {
                    correct += record.completed
                    total += record.attempts
                }
            }
        }
        return NativeJourneySnapshot(startedLessons: started,
                                     practisedLessons: practised,
                                     totalLessons: collection.lessons.count,
                                     recallCorrect: correct,
                                     recallAttempts: total)
    }
}
