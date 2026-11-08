import Foundation

/// Source-anchored whole-word Polish sound examples. There is no separate
/// letter-name/phoneme audio, native acoustic certification or generated TTS.
struct NativeSoundRecord: Decodable, Identifiable {
    let label: String?
    let id: String
    let polish: String
    let english: String
    let focus: String
    let audio: String
    let groupId: String?
}

struct NativeSoundLesson: Decodable, Identifiable {
    let lessonId: String
    let title: String
    let intro: String
    let groups: [SoundGroup]
    let questions: [NativeSoundRecord]

    var id: String { lessonId }
}

struct NativeSoundStudio: Decodable {
    let schemaVersion: Int
    let editorialStatus: String
    let letters: [NativeSoundRecord]
    let combinations: [NativeSoundRecord]
    let soundLessons: [NativeSoundLesson]

    static func load(lessons: [Lesson], bundle: Bundle = .main) throws -> NativeSoundStudio {
        guard let url = bundle.url(forResource: "sound-studio", withExtension: "json",
                                   subdirectory: "generated") else {
            throw CatalogLoadError.invalid("Recorded alphabet and sound lab missing")
        }
        let data = try JSONDecoder().decode(NativeSoundStudio.self, from: Data(contentsOf: url))
        guard data.schemaVersion == 1,
              data.editorialStatus == "source_only_no_isolated_letter_audio_or_acoustic_certification",
              data.letters.count == 32, data.combinations.count == 13,
              data.soundLessons.count == 5,
              data.soundLessons.reduce(0, { $0 + $1.questions.count }) == 25 else {
            throw CatalogLoadError.invalid("Incomplete or unreviewed sound-learning inventory")
        }
        let expectedLetters = "A Ą B C Ć D E Ę F G H I J K L Ł M N Ń O Ó P R S Ś T U W Y Z Ź Ż"
            .components(separatedBy: " ")
        let expectedCombinations = "CZ SZ RZ CH SI ZI DZI NI SZCZ TRZ PRZ KRZ DZ"
            .components(separatedBy: " ")
        guard data.letters.compactMap(\.label) == expectedLetters,
              data.combinations.compactMap(\.label) == expectedCombinations else {
            throw CatalogLoadError.invalid("Letter or combination ordering changed")
        }

        let original = Dictionary(uniqueKeysWithValues: lessons.flatMap(\.items).map { ($0.id, $0) })
        let sourceLessons = Dictionary(uniqueKeysWithValues: lessons.map { ($0.id, $0) })
        for record in data.letters + data.combinations {
            guard let at = record.id.lastIndex(of: ":"),
                  let owner = sourceLessons[String(record.id[..<at])],
                  owner.source == "legacy" && owner.kind == "vocabulary",
                  let row = original[record.id],
                  row.polish == record.polish, row.english == record.english,
                  row.audio == record.audio, row.referenceReview != "practice_only",
                  record.polish.components(separatedBy: record.focus).count == 2,
                  !record.focus.isEmpty,
                  AudioFiles.referenceURL(for: record.audio, bundle: bundle) != nil else {
                throw CatalogLoadError.invalid("Changed recorded alphabet word: " + record.id)
            }
        }
        var seen = Set<String>()
        for entry in data.soundLessons {
            guard seen.insert(entry.id).inserted,
                  let owner = sourceLessons[entry.lessonId],
                  owner.source == "curated", owner.kind == "sounds",
                  owner.soundGroups?.count == entry.groups.count,
                  (4...8).contains(entry.questions.count),
                  Set(entry.questions.map(\.id)).count == entry.questions.count else {
                throw CatalogLoadError.invalid("Changed sound-lab lesson " + entry.id)
            }
            let groups = Dictionary(uniqueKeysWithValues: (owner.soundGroups ?? []).map { ($0.id, $0) })
            var covered = Set<String>()
            for question in entry.questions {
                guard let originalRow = original[question.id],
                      let groupId = question.groupId, let group = groups[groupId],
                      group.itemIds.contains(question.id),
                      originalRow.soundGroupId == groupId,
                      originalRow.soundFocus == question.focus,
                      originalRow.polish == question.polish,
                      originalRow.english == question.english,
                      originalRow.audio == question.audio,
                      originalRow.referenceReview != "practice_only",
                      question.polish.components(separatedBy: question.focus).count == 2,
                      AudioFiles.referenceURL(for: question.audio, bundle: bundle) != nil else {
                    throw CatalogLoadError.invalid("Changed sound recognition card: " + question.id)
                }
                covered.insert(groupId)
            }
            guard covered.count >= 2 else {
                throw CatalogLoadError.invalid("Sound-lab contrast lost its alternatives")
            }
        }
        return data
    }
}
