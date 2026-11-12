import Foundation

/// Private synchronization policy is deliberately stored OUTSIDE LocalLearner,
/// owner-exported JSON and any family account. It owns no CloudKit transport.
/// In particular, deleting or restoring learning history NEVER deletes or
/// silently resets a pending *remote* deletion tombstone.
enum NativePrivateCloudStoreError: LocalizedError, Equatable {
    case invalidFile
    case writeFailed

    var errorDescription: String? {
        switch self {
        case .invalidFile:
            return "Private synchronization safety state could not be read. Cloud access remains blocked; the original file is preserved."
        case .writeFailed:
            return "Private synchronization state could not be saved. No state change was applied."
        }
    }
}

@MainActor
final class NativePrivateCloudGateStore {
    private(set) var gate: NativePrivateCloudGate
    private let storageURL: URL

    /// No file = disabled: first launch does not contact Apple or create
    /// an account. A malformed existing file is NOT silently treated as off;
    /// that could erase an outstanding remote-delete lockout.
    init(storageURL: URL) throws {
        self.storageURL = storageURL
        if FileManager.default.fileExists(atPath: storageURL.path) {
            let bytes: Data
            do {
                bytes = try Self.readBounded(storageURL)
            } catch {
                throw NativePrivateCloudStoreError.invalidFile
            }
            let recovered: NativePrivateCloudGate
            do {
                recovered = try JSONDecoder().decode(NativePrivateCloudGate.self,
                                                      from: bytes)
                try recovered.validatePersistedState()
            } catch {
                throw NativePrivateCloudStoreError.invalidFile
            }
            gate = recovered
        } else {
            gate = NativePrivateCloudGate()
        }
    }

    /// Applies a change to a detached copy and atomically commits it BEFORE
    /// publishing the next state. If any operation or file write fails, both
    /// the last known policy and its on-disk state remain unchanged.
    /// Future CloudKit code must not bypass this transaction for opt-in,
    /// account changes, opt-out, tombstone requests or acknowledgements.
    func commit(_ change: (inout NativePrivateCloudGate) throws -> Void) throws {
        var staged = gate
        try change(&staged)
        try staged.validatePersistedState()
        let encoded = try JSONEncoder().encode(staged)
        guard encoded.count <= 16_384 else {
            throw NativePrivateCloudStoreError.writeFailed
        }
        do {
            let directory = storageURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(
                at: directory, withIntermediateDirectories: true)
            try encoded.write(to: storageURL,
                              options: [.atomic, .completeFileProtectionUnlessOpen])
        } catch {
            throw NativePrivateCloudStoreError.writeFailed
        }
        gate = staged
    }

    private static func readBounded(_ url: URL) throws -> Data {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let bytes = try handle.read(upToCount: 16_385) ?? Data()
        guard !bytes.isEmpty, bytes.count <= 16_384 else {
            throw NativePrivateCloudStoreError.invalidFile
        }
        return bytes
    }
}
