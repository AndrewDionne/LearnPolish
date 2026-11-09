import Foundation

/// Import is **replacement only**, never a merge, and never links a family
/// account or CloudKit identity. This validates a supplied archive against the
/// exact ORIGINAL V2 catalog before it can be shown in a confirmation screen.
enum LocalRestoreValidation {
    static func validate(_ archive: LocalProgressArchive,
                         lessons: [Lesson],
                         regions: [PolandRegion],
                         guided: [GuidedFoundationStep],
                         touristUnits: [TouristUnit],
                         core: CoreJourney?) throws {
        try archive.validate()
        let expectedLessons = Set(lessons.map(\.id))
        guard Set(archive.sourceLessonIDs) == expectedLessons,
              archive.sourceLessonIDs.count == expectedLessons.count,
              expectedLessons.count == 26 else {
            throw LocalProgressArchiveError.incompatibleCatalog
        }
        let profile = archive.profile
        let byItem = Dictionary(uniqueKeysWithValues: lessons.flatMap { lesson in
            lesson.items.map { ($0.id, (lesson, $0)) }
        })
        let byLesson = Dictionary(uniqueKeysWithValues: lessons.map { ($0.id, $0) })
        let knownRegions = Set(regions.map(\.id))
        let knownSteps = Dictionary(uniqueKeysWithValues: guided.map { ($0.id, $0) })
        let unitByID = Dictionary(uniqueKeysWithValues: touristUnits.map { ($0.id, $0) })

        guard profile.firstOpened.timeIntervalSince1970.isFinite,
              profile.records.count <= 100_000 else {
            throw LocalProgressArchiveError.invalid
        }
        if let id = profile.lastLessonID, byLesson[id] == nil {
            throw LocalProgressArchiveError.invalid
        }
        if let id = profile.lastCoreLessonID,
           core?.placements[id] == nil {
            throw LocalProgressArchiveError.invalid
        }
        if let id = profile.lastItemID {
            guard let (owner, _) = byItem[id],
                  profile.lastLessonID == owner.id else {
                throw LocalProgressArchiveError.invalid
            }
        }
        if let id = profile.guidedStepID {
            guard let step = knownSteps[id],
                  profile.guidedItemID == nil ||
                      step.items.contains(where: { $0.id == profile.guidedItemID }) else {
                throw LocalProgressArchiveError.invalid
            }
        } else if profile.guidedItemID != nil {
            throw LocalProgressArchiveError.invalid
        }

        // Archive review counters and navigation are not trusted merely
        // because they came from a JSON file previously named "Progress".
        for (key, record) in profile.records {
            guard let colon = key.firstIndex(of: ":"),
                  let mode = PracticeMode(rawValue: String(key[..<colon])),
                  let (lesson, item) = byItem[String(key[key.index(after: colon)...])],
                  lesson.availableModes.contains(mode),
                  mode != .listen || (item.audio != nil &&
                                      item.referenceReview != "practice_only"),
                  record.attempts >= 0, record.attempts <= 100_000,
                  (0...record.attempts).contains(record.completed),
                  (0...7).contains(record.reviewLevel),
                  record.lastAttempt?.timeIntervalSince1970.isFinite ?? true,
                  record.nextReview?.timeIntervalSince1970.isFinite ?? true else {
                throw LocalProgressArchiveError.invalid
            }
        }

        if let progress = profile.tourist {
            if let unitID = progress.unitID {
                guard let unit = unitByID[unitID],
                      unit.steps.indices.contains(progress.stepIndex),
                      progress.itemID == nil ||
                        unit.steps[progress.stepIndex].items.contains(where: { $0.id == progress.itemID }) else {
                    throw LocalProgressArchiveError.invalid
                }
            } else if progress.itemID != nil {
                throw LocalProgressArchiveError.invalid
            }
            guard progress.attemptedByStep.count <= 30,
                  progress.completedSteps.count <= 30 else {
                throw LocalProgressArchiveError.invalid
            }
            func originalIDs(for key: String) -> Set<String>? {
                let parts = key.split(separator: ":")
                guard parts.count == 2,
                      let unit = unitByID[String(parts[0])],
                      let i = Int(parts[1]), unit.steps.indices.contains(i) else { return nil }
                return Set(unit.steps[i].items.map(\.id))
            }
            for (key, itemIDs) in progress.attemptedByStep {
                guard let originals = originalIDs(for: key),
                      itemIDs.isSubset(of: originals) else {
                    throw LocalProgressArchiveError.invalid
                }
            }
            for key in progress.completedSteps {
                guard let originals = originalIDs(for: key),
                      progress.attemptedByStep[key] == originals else {
                    throw LocalProgressArchiveError.invalid
                }
            }
        }

        if let expedition = profile.expedition {
            guard knownRegions.contains(expedition.selectedRegion),
                  expedition.events.count <= 20_000,
                  expedition.regionGoals.count <= 16,
                  expedition.regionGoals.allSatisfy({ knownRegions.contains($0.key) &&
                                                      $0.value > 0 && $0.value < 1_000_000 }) else {
                throw LocalProgressArchiveError.invalid
            }
            let tierXP = [10, 14, 19, 26, 35]
            var eventIDs = Set<String>()
            for event in expedition.events {
                guard eventIDs.insert(event.id).inserted,
                      let (lesson, item) = byItem[event.itemID],
                      lesson.availableModes.contains(event.mode),
                      event.mode != .listen ||
                          (item.audio != nil && item.referenceReview != "practice_only"),
                      (1...5).contains(event.tier),
                      event.xp == tierXP[event.tier - 1],
                      event.baseXP == event.xp,
                      (0...event.xp).contains(event.expeditionXP),
                      knownRegions.contains(event.regionID),
                      expedition.regionGoals[event.regionID] != nil,
                      event.at.timeIntervalSince1970.isFinite,
                      event.id.hasPrefix(event.mode.rawValue + ":" + event.itemID + ":"),
                      event.id.count == event.mode.rawValue.count + event.itemID.count + 12 else {
                    throw LocalProgressArchiveError.invalid
                }
            }
        }

        if let journal = profile.practiceJournal {
            try journal.validateSource(lessons: lessons, regions: regions)
            guard journal.startedAt.timeIntervalSince1970.isFinite,
                  journal.events.allSatisfy({ $0.at <= archive.exportedAt.addingTimeInterval(300) }) else {
                throw LocalProgressArchiveError.invalid
            }
            // Only a fully journalled history can be checked against aggregates;
            // older profiles remain valid without fabricated past events.
            if !journal.hasLegacyHistory {
                let projected = try journal.projectedRecords(lessons: lessons)
                guard projected.count == profile.records.count,
                      projected.allSatisfy({ key, computed in
                          guard let saved = profile.records[key] else { return false }
                          return computed.attempts == saved.attempts &&
                                 computed.completed == saved.completed &&
                                 computed.reviewLevel == saved.reviewLevel &&
                                 computed.lastAttempt == saved.lastAttempt &&
                                 computed.nextReview == saved.nextReview
                      }) else {
                    throw LocalProgressArchiveError.invalid
                }
            }
        }
    }
}
