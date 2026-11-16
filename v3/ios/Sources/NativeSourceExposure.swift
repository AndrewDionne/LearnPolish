import Foundation

struct SourceIntroLine: Decodable, Identifiable {
    let id: String
    let polish: String
    let english: String
    let audio: String
    let teachingCue: String?
}

struct NativeSourceIntroLesson: Decodable, Identifiable {
    let lessonId: String
    let mode: PracticeMode
    let title: String
    let items: [SourceIntroLine]
    var id: String { mode.rawValue + ":" + lessonId }
}

struct NativeSourceExposure: Decodable {
    let schemaVersion: Int
    let editorialStatus: String
    let reading: [NativeSourceIntroLesson]
    let listening: [NativeSourceIntroLesson]

    func preparation(for lesson: Lesson, mode: PracticeMode) -> NativeSourceIntroLesson? {
        if mode == .read {
            return reading.first { $0.lessonId == lesson.id }
        }
        if mode == .listen {
            return (reading + listening).first { $0.lessonId == lesson.id }
        }
        return nil
    }

    static func load(lessons: [Lesson], bundle: Bundle = .main) throws -> NativeSourceExposure {
        guard let url = bundle.url(forResource: "source-exposure", withExtension: "json",
                                   subdirectory: "generated") else {
            throw CatalogLoadError.invalid("Original Read/Listen teaching introductions missing")
        }
        let source = try JSONDecoder().decode(NativeSourceExposure.self,
                                              from: Data(contentsOf: url))
        guard source.schemaVersion == 1,
              source.editorialStatus == "source_only_original_recorded_turns_not_native_reviewed",
              source.reading.count == 6, source.listening.count == 7,
              source.reading.reduce(0, { $0 + $1.items.count }) == 51 else {
            throw CatalogLoadError.invalid("Changed V2 Read/Listen introduction inventory")
        }
        let byID = Dictionary(uniqueKeysWithValues: lessons.map { ($0.id, $0) })
        var identified = Set<String>()
        for introduction in source.reading + source.listening {
            guard identified.insert(introduction.id).inserted,
                  let original = byID[introduction.lessonId],
                  original.source == "legacy",
                  original.kind == (introduction.mode == .read ? "reading" : "vocabulary"),
                  !introduction.items.isEmpty,
                  original.title == introduction.title else {
                throw CatalogLoadError.invalid("Changed original introductory lesson identity")
            }
            let sourceItems = Dictionary(uniqueKeysWithValues: original.items.map { ($0.id, $0) })
            guard Set(introduction.items.map(\.id)).count == introduction.items.count else {
                throw CatalogLoadError.invalid("Duplicate original introductory item")
            }
            var lastIndex = -1
            for line in introduction.items {
                let parts = line.id.split(separator: ":")
                guard let indexText = parts.last, let index = Int(indexText),
                      index > lastIndex,
                      line.id == original.id + ":" + String(index),
                      let item = sourceItems[line.id],
                      item.polish == line.polish, item.english == line.english,
                      item.audio == line.audio, item.referenceReview != "practice_only",
                      AudioFiles.referenceURL(for: line.audio, bundle: bundle) != nil else {
                    throw CatalogLoadError.invalid("Source-first text or original audio changed")
                }
                lastIndex = index
            }
            if introduction.mode == .read && introduction.items.count != original.items.count {
                throw CatalogLoadError.invalid("Reading conversation lost a source turn")
            }
        }
        return source
    }
}
