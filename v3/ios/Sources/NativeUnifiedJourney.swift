import Foundation

/// The *navigation* sequence is a single source-validated Journey 1. Original
/// source lessons, audio, question IDs and prior attempts are not copied.
/// This is an instructional ordering proposal, NOT an independently verified
/// Polish lexical / grammar / phonetic certification.
struct NativeUnifiedJourneyNode: Identifiable {
    let route: PracticeRoute
    let title: String
    let descriptor: String
    let sourceIDs: [String]
    let repeatedSourceCount: Int

    var id: String {
        switch route {
        case .guided(let id): return "g:" + id
        case .lesson(let id): return "l:" + id
        case .soundLab, .scenarios: return "optional"
        }
    }
}

struct NativeUnifiedJourneyChapter: Identifiable {
    let id: String
    let title: String
    let description: String
    let nodes: [NativeUnifiedJourneyNode]
}

struct NativeUnifiedJourneyProgress {
    let practised: Int
    let required: Int

    var started: Bool { practised > 0 }
    var complete: Bool { required > 0 && practised == required }
}

private struct NativeUnifiedJourneySource: Decodable {
    struct Chapter: Decodable {
        let id: String
        let title: String
        let description: String
        let activities: [String]
    }
    let schemaVersion: Int
    let editorialStatus: String
    let notes: String
    let chapters: [Chapter]
}

/// Each source item contributes its ORIGINAL keyed attempt (learn/speak/read
/// or listen), not a new independent grade when repeated in another chapter.
struct NativeUnifiedJourney {
    let chapters: [NativeUnifiedJourneyChapter]

    var nodes: [NativeUnifiedJourneyNode] { chapters.flatMap(\.nodes) }

    /// Explicit, reviewable source IDs; a small unit can be opened in
    /// Practice without a hard lock. The chapter-level sequence supplies a
    /// single recommended "next" across guided, sounds and conversations.

    init(guided: [GuidedFoundationStep], core: CoreJourney,
         bundle: Bundle = .main) throws {
        guard let url = bundle.url(forResource: "unified-journey",
                                   withExtension: "json",
                                   subdirectory: "generated") else {
            throw CatalogLoadError.invalid("Missing reviewed unified journey source")
        }
        let source = try JSONDecoder().decode(
            NativeUnifiedJourneySource.self, from: Data(contentsOf: url))
        guard source.schemaVersion == 1,
              source.editorialStatus ==
                "source-mapped_unified_navigation_not_independently_linguistic_reviewed",
              source.chapters.count == 8,
              Set(source.chapters.map(\.id)).count == 8,
              source.chapters.flatMap(\.activities).count == 35 else {
            throw CatalogLoadError.invalid("Unified Journey 1 authored source drift")
        }
        let byGuided = Dictionary(uniqueKeysWithValues: guided.map { ($0.id, $0) })
        let byCourse = Dictionary(uniqueKeysWithValues: core.ordered.map { ($0.id, $0) })
        let expectedCore = Set(core.ordered.filter {
            core.placements[$0.id]?.journey == 1
        }.map(\.id))
        var seenGuided = Set<String>()
        var seenCore = Set<String>()
        var seenSourceItems = Set<String>()
        var introducedConcepts = Set<String>()
        var authored: [NativeUnifiedJourneyChapter] = []
        for chapter in source.chapters {
            let id = chapter.id
            let title = chapter.title
            let description = chapter.description
            let entries = chapter.activities
            guard !title.isEmpty, !description.isEmpty, !entries.isEmpty,
                  Set(entries).count == entries.count else {
                throw CatalogLoadError.invalid("Duplicate or blank unified activity")
            }
            var nodes: [NativeUnifiedJourneyNode] = []
            for reference in entries {
                let key = String(reference.dropFirst(2))
                let identifiers: [String]
                let route: PracticeRoute
                let name: String
                let caption: String
                if reference.hasPrefix("g:"), let guidedStep = byGuided[key] {
                    guard seenGuided.insert(key).inserted,
                          Set(guidedStep.requires).isSubset(of: introducedConcepts)
                    else {
                        throw CatalogLoadError.invalid("Unified guided prerequisite or duplication: " + key)
                    }
                    introducedConcepts.formUnion(guidedStep.introduces)
                    identifiers = guidedStep.items.map(\.id)
                    route = .guided(key)
                    name = guidedStep.title
                    caption = guidedStep.stage
                } else if reference.hasPrefix("l:"), let lesson = byCourse[key],
                          core.placements[key]?.journey == 1 {
                    guard seenCore.insert(key).inserted else {
                        throw CatalogLoadError.invalid("Unified core duplicate: " + key)
                    }
                    identifiers = lesson.items.map(\.id)
                    route = .lesson(key)
                    name = lesson.title
                    caption = lesson.kind == "sounds" ? "Sound practice" :
                        lesson.kind == "reading" ? "Read or listen" : "Speak and learn"
                } else {
                    throw CatalogLoadError.invalid("Missing unified Journey 1 source: " + reference)
                }
                guard !identifiers.isEmpty,
                      Set(identifiers).count == identifiers.count else {
                    throw CatalogLoadError.invalid("Invalid unified original source item: " + reference)
                }
                let repeats = identifiers.filter { seenSourceItems.contains($0) }.count
                seenSourceItems.formUnion(identifiers)
                nodes.append(NativeUnifiedJourneyNode(
                    route: route, title: name, descriptor: caption,
                    sourceIDs: identifiers, repeatedSourceCount: repeats))
            }
            authored.append(NativeUnifiedJourneyChapter(
                id: id, title: title, description: description, nodes: nodes))
        }
        guard seenGuided == Set(guided.map(\.id)), seenGuided.count == 16,
              seenCore == expectedCore, expectedCore.count == 19,
              authored.count == 8,
              authored.flatMap(\.nodes).count == 35 else {
            throw CatalogLoadError.invalid("Unified Journey 1 original source inventory drift")
        }
        // The original core pilot is deliberately *reordered* to put sound
        // contrasts before a long greeting exercise. Its 19 source lesson
        // IDs and all phrase/attempt IDs remain unchanged.
        chapters = authored
    }

    func node(for route: PracticeRoute) -> NativeUnifiedJourneyNode? {
        nodes.first { $0.route == route }
    }

    func next(after route: PracticeRoute) -> NativeUnifiedJourneyNode? {
        let all = nodes
        guard let position = all.firstIndex(where: { $0.route == route }),
              all.indices.contains(position + 1) else { return nil }
        return all[position + 1]
    }

    func progress(_ node: NativeUnifiedJourneyNode,
                  guided: [GuidedFoundationStep], core: CoreJourney,
                  records: [String: PracticeRecord]) -> NativeUnifiedJourneyProgress {
        switch node.route {
        case .guided(let id):
            guard let step = guided.first(where: { $0.id == id }) else {
                return NativeUnifiedJourneyProgress(practised: 0, required: 0)
            }
            let introductions = step.items.filter {
                GuidedExercisePlan.introduced($0, records: records)
            }.count
            let hasRecap = GuidedExercisePlan.hasRecap(step)
            let recaps = hasRecap ? step.items.filter {
                !GuidedExercisePlan.needsRecap($0, records: records)
            }.count : 0
            return NativeUnifiedJourneyProgress(
                practised: introductions + recaps,
                required: step.items.count * (hasRecap ? 2 : 1))
        case .lesson(let id):
            guard let lesson = core.ordered.first(where: { $0.id == id }) else {
                return NativeUnifiedJourneyProgress(practised: 0, required: 0)
            }
            if let dialogues = lesson.microDialogues, !dialogues.isEmpty {
                let lastIDs = Set(dialogues.compactMap { $0.turns.last?.itemId })
                return NativeUnifiedJourneyProgress(
                    practised: lastIDs.filter {
                        (records["listen:" + $0]?.attempts ?? 0) > 0
                    }.count, required: lastIDs.count)
            }
            let scored = lesson.items.filter { item in
                if lesson.kind == "vocabulary" {
                    // A real original Speak OR Learn attempt is practice.
                    // Becoming eligible for a second recall mode must not
                    // retroactively erase a previously saved introduction.
                    return NativeExercisePlan.introduced(item, records: records)
                }
                let mode = NativeExercisePlan.mode(for: lesson, item: item)
                return (records[mode.rawValue + ":" + item.id]?.attempts ?? 0) > 0
            }.count
            return NativeUnifiedJourneyProgress(
                practised: scored, required: lesson.items.count)
        case .soundLab, .scenarios:
            return NativeUnifiedJourneyProgress(practised: 0, required: 0)
        }
    }

    func nextUnpractised(guided: [GuidedFoundationStep],
                         core: CoreJourney,
                         records: [String: PracticeRecord]) -> NativeUnifiedJourneyNode? {
        nodes.first {
            !progress($0, guided: guided, core: core, records: records).complete
        }
    }

    func progress(_ chapter: NativeUnifiedJourneyChapter,
                  guided: [GuidedFoundationStep],
                  core: CoreJourney,
                  records: [String: PracticeRecord]) -> (practised: Int, started: Int) {
        var completed = 0
        var started = 0
        for node in chapter.nodes {
            let p = progress(node, guided: guided, core: core, records: records)
            if p.complete { completed += 1 }
            if p.started { started += 1 }
        }
        return (completed, started)
    }

    func completedSteps(guided: [GuidedFoundationStep],
                        core: CoreJourney,
                        records: [String: PracticeRecord]) -> Int {
        nodes.filter {
            progress($0, guided: guided, core: core, records: records).complete
        }.count
    }

    /// Answer-based matching only; the same original source ID is counted
    /// once per chapter even if it occurs in two original lesson placements.
    func matchingAccuracy(for chapter: NativeUnifiedJourneyChapter,
                          records: [String: PracticeRecord]) -> Int? {
        let sourceIDs = Set(chapter.nodes.flatMap(\.sourceIDs))
        let numerator = sourceIDs.reduce(0) {
            $0 + (records["learn:" + $1]?.objectiveCorrect ?? 0)
        }
        let denominator = sourceIDs.reduce(0) {
            $0 + (records["learn:" + $1]?.objectiveAttempts ?? 0)
        }
        guard denominator > 0 else { return nil }
        return Int((100.0 * Double(numerator) / Double(denominator)).rounded())
    }
}
