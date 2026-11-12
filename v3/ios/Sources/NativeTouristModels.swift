import Foundation

/// The original V2 tourist plan routes learners through existing audio and
/// original item identities. Unit/step IDs are navigation only, never XP keys.
struct TouristRecordedItem: Decodable, Identifiable {
    let id: String
    let polish: String
    let english: String
    let audio: String
    let comprehension: Comprehension?
}

struct TouristStep: Decodable, Identifiable {
    let mode: PracticeMode
    let lessonId: String
    let title: String
    let items: [TouristRecordedItem]
    var id: String { mode.rawValue + ":" + lessonId }

    func sourceIntroduction(from exposure: NativeSourceExposure?) -> NativeSourceIntroLesson {
        let lesson = (exposure?.reading ?? []) + (exposure?.listening ?? [])
        let sourceLines = lesson.first(where: { $0.lessonId == lessonId })?.items ?? []
        return NativeSourceIntroLesson(
            lessonId: lessonId,
            mode: mode,
            title: title,
            items: items.map { recorded in
                let matching = sourceLines.first(where: {
                    $0.id == recorded.id &&
                    $0.polish == recorded.polish &&
                    $0.english == recorded.english &&
                    $0.audio == recorded.audio
                })
                return SourceIntroLine(id: recorded.id, polish: recorded.polish,
                                       english: recorded.english, audio: recorded.audio,
                                       teachingCue: matching?.teachingCue)
            }
        )
    }
}

struct TouristUnit: Decodable, Identifiable {
    let id: String
    let order: Int
    let journey: Int
    let position: String
    let title: String
    let outcome: String
    let steps: [TouristStep]
    let gaps: [String]?
}

struct TouristCatalog: Decodable {
    let schemaVersion: Int
    let editorialStatus: String
    let units: [TouristUnit]

    static func load(lessons: [Lesson], bundle: Bundle = .main) throws -> TouristCatalog {
        guard let url = bundle.url(forResource: "tourist-units", withExtension: "json",
                                   subdirectory: "generated") else {
            throw CatalogLoadError.invalid("Source-backed tourist activities are missing")
        }
        let data = try JSONDecoder().decode(TouristCatalog.self,
                                            from: Data(contentsOf: url))
        guard data.schemaVersion == 1,
              data.editorialStatus == "source_refs_only_native_review_pending",
              data.units.count == 8,
              data.units.reduce(0, { $0 + $1.steps.count }) == 22 else {
            throw CatalogLoadError.invalid("Original tourist unit inventory changed")
        }
        let byLesson = Dictionary(uniqueKeysWithValues: lessons.map { ($0.id, $0) })
        let expectedModes: [PracticeMode] = [.listen, .speak, .read]
        for (unitIndex, unit) in data.units.enumerated() {
            guard unit.id == "T0" + String(unitIndex + 1),
                  unit.order == unitIndex + 1, unit.journey == 1,
                  unit.position == (unitIndex < 3 ? "beginning" : "middle"),
                  unit.title.count >= 5, unit.outcome.count >= 12,
                  (2...3).contains(unit.steps.count) else {
                throw CatalogLoadError.invalid("Tourist unit order or lesson description changed")
            }
            for (stepIndex, step) in unit.steps.enumerated() {
                guard step.mode == expectedModes[stepIndex],
                      !step.items.isEmpty,
                      let source = byLesson[step.lessonId],
                      source.source != "personal",
                      source.availableModes.contains(step.mode),
                      source.kind == (step.mode == .read ? "reading" : source.kind),
                      (step.mode != .speak || source.kind != "reading"),
                      step.title == source.title,
                      Set(step.items.map(\.id)).count == step.items.count else {
                    throw CatalogLoadError.invalid("Unavailable tourist mode or source: " + unit.id)
                }
                var last = -1
                for record in step.items {
                    guard let at = source.items.firstIndex(where: { $0.id == record.id }),
                          at > last,
                          let original = source.items[safe: at],
                          original.polish == record.polish,
                          original.english == record.english,
                          original.audio == record.audio,
                          original.referenceReview != "practice_only",
                          AudioFiles.referenceURL(for: record.audio, bundle: bundle) != nil,
                          record.id.hasPrefix(source.id + ":") else {
                        throw CatalogLoadError.invalid("Unreviewed tourist recording " + record.id)
                    }
                    last = at
                }
            }
        }
        return data
    }
}

private extension Array {
    subscript(safe index: Int) -> Element? {
        indices.contains(index) ? self[index] : nil
    }
}

struct LocalTouristProgress: Codable {
    var unitID: String?
    var stepIndex: Int = 0
    var itemID: String?
    var attemptedByStep: [String: Set<String>] = [:]
    var completedSteps: Set<String> = []

    static func key(unitID: String, stepIndex: Int) -> String {
        unitID + ":" + String(stepIndex)
    }

    func attemptedCount(unitID: String, stepIndex: Int) -> Int {
        attemptedByStep[Self.key(unitID: unitID, stepIndex: stepIndex)]?.count ?? 0
    }

    func isComplete(unitID: String, stepIndex: Int) -> Bool {
        completedSteps.contains(Self.key(unitID: unitID, stepIndex: stepIndex))
    }
}
