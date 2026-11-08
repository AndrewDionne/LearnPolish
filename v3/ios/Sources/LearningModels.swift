import Foundation

// Swift projection of the existing V2 JSON contract. Unknown editorial fields
// remain in V2 source and are never rewritten by the native app.
struct LessonManifest: Decodable {
    let schemaVersion: Int
    let lessons: [Lesson]
}

struct CurriculumPlacement: Decodable {
    let stage: String
    let track: String
    let order: Int
}

struct LessonItem: Decodable, Identifiable {
    let id: String
    let polish: String
    let english: String
    let pronunciation: String?
    let audio: String?
    let referenceReview: String?
    let comprehension: Comprehension?
    let pronunciationSegments: PronunciationSegments?
}

struct PronunciationSegments: Decodable {
    let method: String
    let segments: [String]
}

struct Comprehension: Decodable {
    let prompt: String
    let options: [String]
    let correctIndex: Int
    let feedback: String
}

struct Lesson: Decodable, Identifiable {
    let schemaVersion: Int
    let id: String
    let title: String
    let description: String?
    let curriculum: CurriculumPlacement?
    let kind: String
    let source: String
    let items: [LessonItem]
    let intro: String?
    let needsReview: Bool?

    var hasAudio: Bool { items.contains { $0.audio != nil } }

    var availableModes: [PracticeMode] {
        switch kind {
        case "reading": return hasAudio ? [.read, .listen] : [.read]
        case "sounds": return hasAudio ? [.listen, .speak] : [.speak]
        default: return hasAudio ? [.learn, .listen, .speak] : [.learn, .speak]
        }
    }

    var stageRank: Int {
        switch curriculum?.stage {
        case "fundamentals": return 0
        case "basic": return 1
        case "learning": return 2
        default: return 3
        }
    }
}

enum PracticeMode: String, CaseIterable, Identifiable, Codable {
    case learn, listen, read, speak
    var id: String { rawValue }
    var label: String { rawValue.capitalized }
    var symbol: String {
        switch self {
        case .learn: return "rectangle.stack"
        case .listen: return "headphones"
        case .read: return "book"
        case .speak: return "mic"
        }
    }
}

enum CatalogLoadError: LocalizedError {
    case missing
    case invalid(String)

    var errorDescription: String? {
        switch self {
        case .missing: return "The bundled Polish lessons are missing. Run the native asset preparation script."
        case .invalid(let reason): return "The lesson catalog failed verification: " + reason
        }
    }
}

enum CatalogLoader {
    static func load(bundle: Bundle = .main) throws -> [Lesson] {
        guard let url = bundle.url(forResource: "lessons", withExtension: "json", subdirectory: "generated") else {
            throw CatalogLoadError.missing
        }
        let manifest = try JSONDecoder().decode(LessonManifest.self, from: Data(contentsOf: url))
        guard manifest.schemaVersion == 1, manifest.lessons.count >= 26 else {
            throw CatalogLoadError.invalid("Unsupported version or incomplete lesson list")
        }
        var identities = Set<String>()
        for lesson in manifest.lessons {
            guard lesson.schemaVersion == 1, !lesson.items.isEmpty,
                  identities.insert(lesson.id).inserted else {
                throw CatalogLoadError.invalid("Duplicate or empty lesson")
            }
            for item in lesson.items {
                guard !item.polish.isEmpty, !item.english.isEmpty,
                      identities.insert(item.id).inserted else {
                    throw CatalogLoadError.invalid("Duplicate or empty item")
                }
                if let seg = item.pronunciationSegments,
                   seg.segments.joined() != item.polish {
                    throw CatalogLoadError.invalid("Invalid pronunciation grouping")
                }
                if let path = item.audio, AudioFiles.referenceURL(for: path, bundle: bundle) == nil {
                    throw CatalogLoadError.invalid("Missing reference audio for " + item.id)
                }
            }
        }
        return manifest.lessons.sorted {
            if $0.stageRank != $1.stageRank { return $0.stageRank < $1.stageRank }
            if $0.curriculum?.order != $1.curriculum?.order {
                return ($0.curriculum?.order ?? Int.max) < ($1.curriculum?.order ?? Int.max)
            }
            return $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending
        }
    }
}
