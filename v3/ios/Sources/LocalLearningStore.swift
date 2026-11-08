import Foundation
import Combine

struct PracticeRecord: Codable {
    var attempts: Int = 0
    var completed: Int = 0
    var reviewLevel: Int = 0
    var lastAttempt: Date?
    var nextReview: Date?
}

struct LocalLearner: Codable {
    // A device-local record identifier, never a login or API credential.
    var localID = UUID()
    var firstOpened = Date()
    var lastLessonID: String?
    var lastItemID: String?
    var lastMode: PracticeMode?
    var records: [String: PracticeRecord] = [:]
}

@MainActor final class LocalLearningStore: ObservableObject {
    @Published private(set) var profile: LocalLearner
    @Published private(set) var lessons: [Lesson] = []
    @Published private(set) var catalogError: String?
    @Published private(set) var saveError: String?

    private let storageURL: URL
    private let canSave: Bool

    init() {
        let directory = FileManager.default.urls(for: .applicationSupportDirectory,
                                                 in: .userDomainMask)[0]
        storageURL = directory.appendingPathComponent("PathToPolish/local-learner.json")
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        if FileManager.default.fileExists(atPath: storageURL.path) {
            do {
                profile = try decoder.decode(LocalLearner.self, from: Data(contentsOf: storageURL))
                canSave = true
            } catch {
                profile = LocalLearner()
                canSave = false
                saveError = "Saved progress could not be loaded. It has been left untouched; no new data will overwrite it."
            }
        } else {
            profile = LocalLearner()
            canSave = true
        }
        do {
            lessons = try CatalogLoader.load()
        } catch {
            catalogError = error.localizedDescription
        }
    }

    var course: [Lesson] { lessons.filter { $0.curriculum?.stage != "practice" } }
    var nextLesson: Lesson? {
        if let id = profile.lastLessonID, let lesson = lessons.first(where: { $0.id == id }) {
            return lesson
        }
        return course.first
    }

    var completedItems: Int {
        Set(profile.records.filter { $0.value.completed > 0 }
            .compactMap { key, _ in key.split(separator: ":", maxSplits: 1).last.map(String.init) }).count
    }

    var attempts: Int { profile.records.values.reduce(0) { $0 + $1.attempts } }

    var dueReviews: [(Lesson, LessonItem)] {
        let now = Date()
        return course.flatMap { lesson in
            lesson.items.compactMap { item -> (Lesson, LessonItem)? in
                guard let record = profile.records["learn:" + item.id],
                      let due = record.nextReview, due <= now else { return nil }
                return (lesson, item)
            }
        }
    }

    func record(for item: LessonItem, mode: PracticeMode) -> PracticeRecord {
        profile.records[mode.rawValue + ":" + item.id] ?? PracticeRecord()
    }

    func rememberPosition(lesson: Lesson, item: LessonItem, mode: PracticeMode) {
        guard profile.lastLessonID != lesson.id ||
              profile.lastItemID != item.id ||
              profile.lastMode != mode else { return }
        profile.lastLessonID = lesson.id
        profile.lastItemID = item.id
        profile.lastMode = mode
        save()
    }

    /// nil = ungraded Speak attempt; never claims pronunciation success.
    func recordAttempt(item: LessonItem, mode: PracticeMode, understood: Bool?) {
        let key = mode.rawValue + ":" + item.id
        var record = profile.records[key] ?? PracticeRecord()
        record.attempts += 1
        record.lastAttempt = Date()
        if understood == true { record.completed += 1 }
        if mode == .learn, let understood {
            if understood {
                record.reviewLevel = min(record.reviewLevel + 1, 7)
                let days = [1, 3, 7, 14, 30, 60, 90][record.reviewLevel - 1]
                record.nextReview = Calendar.current.date(byAdding: .day, value: days, to: Date())
            } else {
                record.reviewLevel = 0
                record.nextReview = Date()
            }
        }
        profile.records[key] = record
        save()
    }

    private func save() {
        guard canSave else { return }
        do {
            let folder = storageURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: folder,
                                                    withIntermediateDirectories: true)
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            let bytes = try encoder.encode(profile)
            try bytes.write(to: storageURL, options: [.atomic, .completeFileProtectionUnlessOpen])
            saveError = nil
        } catch {
            saveError = "Progress could not be saved on this device. Check available storage."
        }
    }
}
