import Foundation

/// OFFLINE policy only. This does not import CloudKit, create an entitlement,
/// store account credentials, or start a request. A future CKSyncEngine adapter
/// must enforce these gates around EVERY private database operation.
enum NativePrivateCloudGateError: LocalizedError, Equatable {
    case explicitConsentRequired
    case incompleteOrUnlinkedJournal
    case unavailableOrChangedAccount
    case unexpectedOwner
    case staleRemoteRevision
    case deletionPending
    case deletedRemoteHistory
    case invalidTransition

    var errorDescription: String? {
        switch self {
        case .explicitConsentRequired:
            return "Private iCloud synchronization needs a separate explicit approval."
        case .incompleteOrUnlinkedJournal:
            return "Local practice history is not ready for safe two-device synchronization."
        case .unavailableOrChangedAccount:
            return "iCloud account access changed. Remote reads and writes are paused."
        case .unexpectedOwner:
            return "This private iCloud history belongs to a different learner or account."
        case .staleRemoteRevision:
            return "The remote copy is older than a known change or deletion."
        case .deletionPending:
            return "Remote deletion is awaiting authoritative server confirmation."
        case .deletedRemoteHistory:
            return "This history was deleted remotely and cannot be recreated from stale data."
        case .invalidTransition:
            return "The requested private-sync state change is not permitted."
        }
    }
}

struct NativePrivateCloudScope: Codable, Equatable {
    /// Stable opaque account key supplied only by a *verified* future CloudKit
    /// adapter. Never an Apple email, family account or login token.
    let accountKey: String
    let learnerID: UUID
    let journalEpoch: UUID
}

struct NativePrivateCloudTombstone: Codable, Equatable {
    let scope: NativePrivateCloudScope
    /// Monotonic generation; the CK adapter must publish this with
    /// compare-and-swap before claiming any remote deletion completed.
    let generation: UInt64
}

struct NativePrivateCloudSnapshot: Codable {
    let scope: NativePrivateCloudScope
    let generation: UInt64
}

struct NativePrivateCloudGate: Codable {
    enum Phase: String, Codable {
        case off, active, pausedAccountChange, deletionPending, remotelyDeleted
    }

    private(set) var phase: Phase = .off
    private(set) var scope: NativePrivateCloudScope?
    private(set) var knownGeneration: UInt64 = 0
    private(set) var requestedTombstone: NativePrivateCloudTombstone?

    /// Defensive decoding contract for the *separate*, device-local
    /// synchronization policy file. A corrupt file must never make the
    /// application resume remote writes or forget a pending tombstone.
    func validatePersistedState() throws {
        let empty = UUID(uuidString: "00000000-0000-0000-0000-000000000000")!
        if let scope {
            guard (8...200).contains(scope.accountKey.count),
                  !scope.accountKey.contains("@"),
                  !scope.accountKey.contains(" "),
                  scope.learnerID != empty,
                  scope.journalEpoch != empty else {
                throw NativePrivateCloudGateError.invalidTransition
            }
        }
        switch phase {
        case .off:
            guard requestedTombstone == nil,
                  scope != nil || knownGeneration == 0 else {
                throw NativePrivateCloudGateError.invalidTransition
            }
        case .active, .pausedAccountChange:
            guard scope != nil, requestedTombstone == nil else {
                throw NativePrivateCloudGateError.invalidTransition
            }
        case .deletionPending:
            guard let scope, let requestedTombstone,
                  requestedTombstone.scope == scope,
                  knownGeneration < UInt64.max,
                  requestedTombstone.generation == knownGeneration + 1 else {
                throw NativePrivateCloudGateError.invalidTransition
            }
        case .remotelyDeleted:
            guard scope != nil, requestedTombstone == nil,
                  knownGeneration > 0 else {
                throw NativePrivateCloudGateError.invalidTransition
            }
        }
    }

    /// Only a fully source-verified, complete journal with an explicitly
    /// accepted UTC linked epoch is eligible even to PROPOSE CloudKit opt-in.
    /// No account request occurs here and no child consent is implied.
    mutating func proposeExplicitOptIn(
        approved: Bool,
        verifiedOpaqueAccountKey: String?,
        learner: LocalLearner,
        lessons: [Lesson],
        regions: [PolandRegion]
    ) throws {
        guard approved else { throw NativePrivateCloudGateError.explicitConsentRequired }
        guard phase == .off, scope == nil, requestedTombstone == nil else {
            throw NativePrivateCloudGateError.invalidTransition
        }
        guard let account = verifiedOpaqueAccountKey,
              (8...200).contains(account.count),
              !account.contains("@"), !account.contains(" ") else {
            throw NativePrivateCloudGateError.unavailableOrChangedAccount
        }
        guard let journal = learner.practiceJournal,
              !journal.hasLegacyHistory,
              learner.linkedUTCEpoch == journal.epochID else {
            throw NativePrivateCloudGateError.incompleteOrUnlinkedJournal
        }
        do {
            try journal.validateSource(lessons: lessons, regions: regions)
            let projected = try NativeXPReconciliation.candidate(
                journal: journal, lessons: lessons)
            _ = try projected.projectedRegions(verifiedSourceRegions: regions)
        } catch {
            throw NativePrivateCloudGateError.incompleteOrUnlinkedJournal
        }
        scope = NativePrivateCloudScope(accountKey: account,
                                         learnerID: learner.localID,
                                         journalEpoch: journal.epochID)
        phase = .active
        knownGeneration = 0
    }

    /// Changing or losing the iCloud account must not switch remote stores
    /// implicitly. Even when the prior account returns, an explicit resume
    /// action remains necessary.
    mutating func observeAccount(_ verifiedOpaqueAccountKey: String?) {
        guard phase == .active, let scope else { return }
        if verifiedOpaqueAccountKey != scope.accountKey {
            phase = .pausedAccountChange
        }
    }

    mutating func resumeSameAccount(
        approved: Bool, verifiedOpaqueAccountKey: String?
    ) throws {
        guard approved else { throw NativePrivateCloudGateError.explicitConsentRequired }
        guard phase == .pausedAccountChange || phase == .off,
              let scope, requestedTombstone == nil else {
            throw NativePrivateCloudGateError.invalidTransition
        }
        guard verifiedOpaqueAccountKey == scope.accountKey else {
            throw NativePrivateCloudGateError.unavailableOrChangedAccount
        }
        phase = .active
    }

    /// Stopping sync does not delete cloud records, device history, or make
    /// an account switch safe; the bound scope is retained for explicit resume.
    mutating func optOutKeepLocalData() throws {
        guard phase == .active || phase == .pausedAccountChange else {
            if phase == .deletionPending {
                throw NativePrivateCloudGateError.deletionPending
            }
            throw NativePrivateCloudGateError.invalidTransition
        }
        phase = .off
    }

    /// An adapter may consider reading/writing only while the verified
    /// original account, anonymous learner and journal epoch still match.
    func authorizeRemoteOperation(verifiedOpaqueAccountKey: String?,
                                  learner: LocalLearner,
                                  snapshot: NativePrivateCloudSnapshot) throws {
        if phase == .remotelyDeleted {
            throw NativePrivateCloudGateError.deletedRemoteHistory
        }
        if phase == .deletionPending {
            throw NativePrivateCloudGateError.deletionPending
        }
        guard phase == .active, let scope else {
            throw NativePrivateCloudGateError.unavailableOrChangedAccount
        }
        guard verifiedOpaqueAccountKey == scope.accountKey else {
            throw NativePrivateCloudGateError.unavailableOrChangedAccount
        }
        guard learner.localID == scope.learnerID,
              learner.linkedUTCEpoch == scope.journalEpoch,
              snapshot.scope == scope else {
            throw NativePrivateCloudGateError.unexpectedOwner
        }
        guard snapshot.generation >= knownGeneration else {
            throw NativePrivateCloudGateError.staleRemoteRevision
        }
    }

    /// Commit only a server-verified revision, never a local guessed
    /// generation. A future adapter must persist this checkpoint after
    /// successfully saving an atomic CloudKit record.
    mutating func observeVerifiedServerRevision(
        _ confirmed: NativePrivateCloudSnapshot
    ) throws {
        guard phase == .active,
              let scope,
              confirmed.scope == scope,
              confirmed.generation >= knownGeneration,
              confirmed.generation > 0 else {
            throw NativePrivateCloudGateError.staleRemoteRevision
        }
        knownGeneration = confirmed.generation
    }

    /// This is a tombstone *proposal*, not a deletion claim. The future
    /// adapter must publish it via server-checked conditional change and
    /// verify the remote acknowledgement before clearing anything.
    mutating func requestRemoteErase(
        approved: Bool, verifiedOpaqueAccountKey: String?
    ) throws -> NativePrivateCloudTombstone {
        guard approved else { throw NativePrivateCloudGateError.explicitConsentRequired }
        guard phase == .active, let scope else {
            throw NativePrivateCloudGateError.invalidTransition
        }
        guard verifiedOpaqueAccountKey == scope.accountKey else {
            throw NativePrivateCloudGateError.unavailableOrChangedAccount
        }
        guard knownGeneration < UInt64.max else {
            throw NativePrivateCloudGateError.invalidTransition
        }
        let request = NativePrivateCloudTombstone(
            scope: scope, generation: knownGeneration + 1)
        requestedTombstone = request
        phase = .deletionPending
        return request
    }

    /// No local history is deleted by a remote acknowledgement. Every client
    /// must see the authoritative tombstone before remote event uploads resume.
    mutating func acknowledgeServerTombstone(
        _ verifiedServerTombstone: NativePrivateCloudTombstone
    ) throws {
        guard phase == .deletionPending,
              let requestedTombstone, let scope,
              verifiedServerTombstone.scope == scope,
              verifiedServerTombstone.generation >= requestedTombstone.generation else {
            throw NativePrivateCloudGateError.invalidTransition
        }
        knownGeneration = verifiedServerTombstone.generation
        phase = .remotelyDeleted
        self.requestedTombstone = nil
    }

    /// Another phone's server-confirmed deletion must win over any stale
    /// local snapshot. An unverified value cannot serve as the acknowledgement.
    mutating func observeVerifiedServerDeletion(
        _ verifiedServerTombstone: NativePrivateCloudTombstone
    ) throws {
        guard let scope, verifiedServerTombstone.scope == scope,
              verifiedServerTombstone.generation >= knownGeneration else {
            throw NativePrivateCloudGateError.unexpectedOwner
        }
        knownGeneration = verifiedServerTombstone.generation
        requestedTombstone = nil
        phase = .remotelyDeleted
    }
}
