import Foundation

struct GuidedFoundationManifest: Decodable {
    let schemaVersion: Int
    let sourceStatus: String
    let lessonReviewStatus: String
    let steps: [GuidedFoundationStep]
}

struct GuidedRecordedItem: Decodable, Identifiable {
    let id: String
    let polish: String
    let english: String
    let audio: String
    let focus: String?
}

struct GuidedFoundationStep: Decodable, Identifiable {
    let id: String
    let order: Int
    let stage: String
    let type: String
    let title: String
    let requires: [String]
    let introduces: [String]
    let cue: String?
    let explanation: String?
    let items: [GuidedRecordedItem]

    var isGrammar: Bool { type == "grammar" }
}

enum GuidedFoundationPath {
    private static let ids = [
        "simple-replies", "politeness", "greetings", "street-words",
        "transport-words", "everyday-replies", "grammar:requests",
        "grammar:where", "grammar:permission", "grammar:prices",
        "grammar:yes-no-questions", "grammar:negative", "grammar:one-two",
        "food-requests", "shopping-questions", "location-questions"
    ]
    private static let counts = [2,3,3,6,6,5,4,5,4,3,4,4,4,5,5,5]

    static func load(lessons: [Lesson], bundle: Bundle = .main) throws -> [GuidedFoundationStep] {
        guard let url = bundle.url(forResource: "guided-foundations", withExtension: "json",
                                   subdirectory: "generated") else {
            throw CatalogLoadError.invalid("Guided first-word and grammar lessons are missing")
        }
        let result = try JSONDecoder().decode(GuidedFoundationManifest.self, from: Data(contentsOf: url))
        guard result.schemaVersion == 1,
              result.sourceStatus == "authoritative_dependency_inventory_requires_independent_full_lexical_review",
              result.lessonReviewStatus == "source_only_not_independently_native_certified",
              result.steps.map(\.id) == ids else {
            throw CatalogLoadError.invalid("The guided foundation source or order has changed")
        }
        let original = Dictionary(uniqueKeysWithValues: lessons.flatMap { $0.items }.map { ($0.id, $0) })
        let allowedLessons = Dictionary(uniqueKeysWithValues: lessons.map { ($0.id, $0) })
        let stages = ["First words", "Basic vocabulary", "First sentences / basic grammar"]
        var taught = Set<String>()
        for (index, step) in result.steps.enumerated() {
            let expectedStage = index < 3 ? stages[0] : (index < 6 ? stages[1] : stages[2])
            let grammar = (6...12).contains(index)
            guard step.order == index + 1, step.stage == expectedStage,
                  step.isGrammar == grammar,
                  step.type == (grammar ? "grammar" : "words"),
                  step.items.count == counts[index],
                  Set(step.items.map(\.id)).count == step.items.count,
                  Set(step.requires).count == step.requires.count,
                  Set(step.introduces).count == step.introduces.count,
                  !step.introduces.isEmpty,
                  step.requires.allSatisfy({ taught.contains($0) }),
                  step.introduces.allSatisfy({ !taught.contains($0) }) else {
                throw CatalogLoadError.invalid("A guided step has missing or forward prerequisites")
            }
            if grammar && ((step.cue?.isEmpty ?? true) || (step.explanation?.isEmpty ?? true)) {
                throw CatalogLoadError.invalid("Grammar guidance missing for " + step.id)
            }
            for entry in step.items {
                let cut = entry.id.lastIndex(of: ":")
                guard let cut,
                      let lesson = allowedLessons[String(entry.id[..<cut])],
                      lesson.source == "legacy" && lesson.kind == "vocabulary",
                      let source = original[entry.id],
                      source.polish == entry.polish, source.english == entry.english,
                      source.audio == entry.audio, source.referenceReview != "practice_only",
                      AudioFiles.referenceURL(for: entry.audio, bundle: bundle) != nil else {
                    throw CatalogLoadError.invalid("Guided recorded item changed: " + entry.id)
                }
                if grammar {
                    guard let focus = entry.focus, !focus.isEmpty,
                          entry.polish.components(separatedBy: focus).count == 2 else {
                        throw CatalogLoadError.invalid("Invalid grammar focus for " + entry.id)
                    }
                } else if entry.focus != nil {
                    throw CatalogLoadError.invalid("Unapproved word-level grammar hint")
                }
            }
            taught.formUnion(step.introduces)
        }
        return result.steps
    }
}
