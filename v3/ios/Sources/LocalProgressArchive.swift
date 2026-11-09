import Foundation
import SwiftUI
import UniformTypeIdentifiers

/// Versioned user-initiated, unencrypted JSON export of the LOCAL learner only.
/// No account credentials, family memberships, network activity receipts,
/// microphone takes, provider scores or CloudKit records exist in this model.
struct LocalProgressArchive: Codable {
    static let currentFormat = "path-to-polish-local-progress"
    static let currentVersion = 1
    let format: String
    let schemaVersion: Int
    let exportedAt: Date
    let sourceLessonIDs: [String]
    let profile: LocalLearner

    init(profile: LocalLearner, sourceLessonIDs: [String], exportedAt: Date = Date()) {
        format = Self.currentFormat
        schemaVersion = Self.currentVersion
        self.exportedAt = exportedAt
        self.sourceLessonIDs = sourceLessonIDs.sorted()
        self.profile = profile
    }

    func validate() throws {
        guard format == Self.currentFormat,
              schemaVersion == Self.currentVersion,
              !sourceLessonIDs.isEmpty, sourceLessonIDs.count <= 1000,
              Set(sourceLessonIDs).count == sourceLessonIDs.count,
              profile.records.count <= 100_000,
              (profile.expedition?.events.count ?? 0) <= 20_000,
              (profile.practiceJournal?.schemaVersion ?? 1) == NativePracticeJournal.currentSchema,
              (profile.practiceJournal?.events.count ?? 0) <= NativePracticeJournal.maximumEvents,
              profile.records.allSatisfy({
                  !$0.key.isEmpty && $0.value.attempts >= 0 &&
                  $0.value.completed >= 0 &&
                  $0.value.completed <= $0.value.attempts &&
                  (0...7).contains($0.value.reviewLevel)
              }) else {
            throw LocalProgressArchiveError.invalid
        }
    }

    func encoded() throws -> Data {
        try validate()
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let bytes = try encoder.encode(self)
        guard bytes.count <= 16_000_000 else {
            throw LocalProgressArchiveError.invalid
        }
        return bytes
    }

    static func decode(_ bytes: Data) throws -> Self {
        guard bytes.count <= 16_000_000 else {
            throw LocalProgressArchiveError.invalid
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let archive = try decoder.decode(Self.self, from: bytes)
        try archive.validate()
        return archive
    }
}

enum LocalProgressArchiveError: Error, LocalizedError {
    case unavailable, invalid, resetFailed

    var errorDescription: String? {
        switch self {
        case .unavailable:
            return "Progress cannot be exported while a saved file needs recovery or storage is unavailable."
        case .invalid:
            return "The progress export is incomplete or is not a supported Path to Polish archive."
        case .resetFailed:
            return "Local progress could not be erased. No reset was applied."
        }
    }
}

/// Export-only UI. FileDocument's read initializer validates the file, but
/// V3 does not yet expose Import, CloudKit merge or silent backup restoration.
struct LocalProgressArchiveDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.json] }
    let archive: LocalProgressArchive

    init(archive: LocalProgressArchive) throws {
        try archive.validate()
        self.archive = archive
    }

    init(configuration: ReadConfiguration) throws {
        guard let bytes = configuration.file.regularFileContents else {
            throw LocalProgressArchiveError.invalid
        }
        archive = try LocalProgressArchive.decode(bytes)
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: try archive.encoded())
    }
}
