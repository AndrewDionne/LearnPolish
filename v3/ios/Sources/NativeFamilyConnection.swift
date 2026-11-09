import Foundation
import Combine

// V2 private family API only. The account is always optional: the local course,
// microphone and personal XP never depend on these models or this client.
struct NativeFamilyIdentity: Decodable, Equatable {
    let id: Int
    let name: String
    let email: String?
}

struct NativeFamilyGroup: Decodable, Identifiable, Equatable {
    let id: Int
    let name: String
}

struct NativeFamilyLoginReply: Decodable {
    let token: String
    let user: NativeFamilyIdentity
}

struct NativeFamilyMeReply: Decodable {
    let user: NativeFamilyIdentity
    let families: [NativeFamilyGroup]
}

struct NativeFamilySummary: Decodable {
    struct Group: Decodable {
        let id: Int
        let name: String
    }
    struct Member: Decodable, Identifiable {
        let id: Int
        let name: String
        let weekly_xp: Int
        let active_days: Int
        let highest_tier: Int
        let team_xp: Int
    }
    struct Region: Decodable {
        let region: String
        let earned: Int
        let target: Int
        let unlocked: Bool
    }
    struct Totals: Decodable {
        let weekly_xp: Int
        let regions_unlocked: Int
    }
    let group: Group
    let members: [Member]
    let regions: [Region]
    let totals: Totals
}

enum NativeFamilyError: Error, LocalizedError, Equatable {
    case invalidOrigin
    case invalidCredentials
    case verificationRequired
    case tooManyAttempts
    case notAuthorized
    case unavailable
    case malformedResponse
    case cancelled
    case notShareable
    case alreadySharing
    case adultPilotOnly

    var errorDescription: String? {
        switch self {
        case .invalidOrigin: return "Use the HTTPS address of your private family service."
        case .invalidCredentials: return "Those account details were not accepted."
        case .verificationRequired: return "Verify your existing account email before connecting."
        case .tooManyAttempts: return "Too many attempts. Try again later."
        case .notAuthorized: return "Your private family session is unavailable. Sign in again."
        case .unavailable: return "The optional family service is unavailable. Offline learning still works."
        case .malformedResponse: return "The family service returned an unexpected response."
        case .cancelled: return "Connection was cancelled."
        case .notShareable: return "Only a new practice activity from this connected session can be shared."
        case .alreadySharing: return "This activity is already being shared."
        case .adultPilotOnly: return "Connected family and cloud pronunciation are currently restricted to adults. Offline lessons remain available to everyone."
        }
    }
}

/// No redirect to a third-party login, path injection or unencrypted password.
/// The private endpoint is supplied *only when the user chooses to connect*.
struct NativeFamilyOrigin: Equatable {
    let url: URL

    init(text: String) throws {
        let input = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard input.count <= 256,
              let url = URL(string: input),
              url.scheme == "https",
              let host = url.host, !host.isEmpty, !host.contains("*"),
              url.user == nil, url.password == nil,
              url.query == nil, url.fragment == nil,
              url.path.isEmpty || url.path == "/" else {
            throw NativeFamilyError.invalidOrigin
        }
        self.url = url
    }

    func route(_ name: String) -> URL {
        url.appendingPathComponent("api/v2/family/" + name)
    }
}

struct NativeFamilyAccount {
    let origin: NativeFamilyOrigin
    let token: String
    let user: NativeFamilyIdentity
    let groups: [NativeFamilyGroup]
}

/// URLSession is injectable so XCTest uses only URLProtocol mocks. All real
/// sessions are ephemeral (no cookie jar, disk cache, persistent credentials).
struct NativeFamilyAPI {
    let session: URLSession

    init(session: URLSession? = nil) {
        if let session {
            self.session = session
        } else {
            let config = URLSessionConfiguration.ephemeral
            config.timeoutIntervalForRequest = 15
            config.timeoutIntervalForResource = 15
            config.urlCache = nil
            config.httpCookieStorage = nil
            self.session = URLSession(configuration: config)
        }
    }

    static func request(origin: NativeFamilyOrigin, route: String,
                        method: String, token: String? = nil, body: Data? = nil) -> URLRequest {
        var req = URLRequest(url: origin.route(route),
                             cachePolicy: .reloadIgnoringLocalCacheData,
                             timeoutInterval: 15)
        req.httpMethod = method
        req.httpShouldHandleCookies = false
        req.setValue("no-store", forHTTPHeaderField: "Cache-Control")
        if let token {
            req.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        }
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = body
        }
        return req
    }

    private func perform(_ req: URLRequest) async throws -> Data {
        let bytes: Data
        let response: URLResponse
        do { (bytes, response) = try await session.data(for: req) }
        catch {
            if Task.isCancelled { throw NativeFamilyError.cancelled }
            throw NativeFamilyError.unavailable
        }
        guard !Task.isCancelled else { throw NativeFamilyError.cancelled }
        guard let http = response as? HTTPURLResponse else {
            throw NativeFamilyError.malformedResponse
        }
        switch http.statusCode {
        case 200...299:
            guard bytes.count <= 65_536 else { throw NativeFamilyError.malformedResponse }
            return bytes
        case 401: throw NativeFamilyError.invalidCredentials
        case 403: throw NativeFamilyError.verificationRequired
        case 429: throw NativeFamilyError.tooManyAttempts
        default: throw NativeFamilyError.unavailable
        }
    }

    func signIn(origin: NativeFamilyOrigin, email: String, password: String) async throws -> NativeFamilyAccount {
        let email = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard email.count >= 5, email.count <= 250, email.contains("@"),
              !password.isEmpty, password.count <= 1_024 else {
            throw NativeFamilyError.invalidCredentials
        }
        let body = try JSONSerialization.data(withJSONObject: [
            "email": email, "password": password
        ])
        let loginData = try await perform(Self.request(origin: origin, route: "login",
                                                       method: "POST", body: body))
        guard let login = try? JSONDecoder().decode(NativeFamilyLoginReply.self, from: loginData),
              (30...256).contains(login.token.count),
              login.token.rangeOfCharacter(from: .whitespacesAndNewlines) == nil,
              login.user.id > 0, !login.user.name.isEmpty else {
            throw NativeFamilyError.malformedResponse
        }

        // The independently authenticated /me call ensures this token really
        // belongs to the email-verified existing account before Speech connects.
        let data = try await perform(Self.request(origin: origin, route: "me",
                                                   method: "GET", token: login.token))
        guard let account = try? JSONDecoder().decode(NativeFamilyMeReply.self, from: data),
              account.user.id == login.user.id,
              account.user.name == login.user.name,
              !account.user.name.isEmpty,
              Set(account.families.map(\.id)).count == account.families.count,
              account.families.allSatisfy({ $0.id > 0 && !$0.name.isEmpty }) else {
            throw NativeFamilyError.malformedResponse
        }
        return NativeFamilyAccount(origin: origin, token: login.token,
                                   user: account.user, groups: account.families)
    }

    func summary(for group: NativeFamilyGroup,
                 account: NativeFamilyAccount) async throws -> NativeFamilySummary {
        guard account.groups.contains(group) else {
            throw NativeFamilyError.notAuthorized
        }
        let path = "groups/" + String(group.id) + "/summary"
        let data = try await perform(Self.request(origin: account.origin, route: path,
                                                  method: "GET", token: account.token))
        let canonicalRegions = Set((try? PolandRegionCatalog.load())?.map(\.id) ?? [])
        guard let summary = try? JSONDecoder().decode(NativeFamilySummary.self, from: data),
              summary.group.id == group.id, summary.group.name == group.name,
              (1...12).contains(summary.members.count),
              Set(summary.members.map(\.id)).count == summary.members.count,
              summary.members.allSatisfy({
                  $0.id > 0 && !$0.name.isEmpty && $0.weekly_xp >= 0 &&
                  $0.team_xp >= 0 && $0.active_days >= 0 && (0...5).contains($0.highest_tier)
              }),
              summary.regions.count <= canonicalRegions.count,
              Set(summary.regions.map(\.region)).count == summary.regions.count,
              summary.regions.allSatisfy({
                  canonicalRegions.contains($0.region) && $0.earned >= 0 &&
                  $0.target > 0 && $0.unlocked == ($0.earned >= $0.target)
              }),
              summary.totals.weekly_xp >= 0,
              summary.totals.regions_unlocked == summary.regions.filter(\.unlocked).count else {
            throw NativeFamilyError.malformedResponse
        }
        return summary
    }

    /// V2 is the ONLY authority that computes group XP; callers cannot send
    /// client XP, dates, score, recording or result content.
    static func activityRequest(account: NativeFamilyAccount,
                                group: NativeFamilyGroup, event: LocalXPEvent) throws -> URLRequest {
        guard account.groups.contains(group), event.regionID.count <= 40,
              event.itemID.count <= 180, (1...5).contains(event.tier) else {
            throw NativeFamilyError.notAuthorized
        }
        let payload = try JSONSerialization.data(withJSONObject: [
            "item_id": event.itemID, "mode": event.mode.rawValue, "region": event.regionID
        ])
        return request(origin: account.origin,
                       route: "groups/" + String(group.id) + "/activity",
                       method: "POST", token: account.token, body: payload)
    }

    func shareActivity(event: LocalXPEvent, to group: NativeFamilyGroup,
                       account: NativeFamilyAccount) async throws -> NativeFamilyActivityReceipt {
        let req = try Self.activityRequest(account: account, group: group, event: event)
        let data: Data
        do {
            data = try await perform(req)
        } catch NativeFamilyError.invalidCredentials {
            throw NativeFamilyError.notAuthorized
        } catch NativeFamilyError.verificationRequired {
            throw NativeFamilyError.notAuthorized
        }
        return try NativeFamilyActivityGuard.receipt(data, source: event)
    }

    func logOut(account: NativeFamilyAccount) async {
        let request = Self.request(origin: account.origin, route: "logout",
                                   method: "POST", token: account.token)
        // Best effort; local credentials are cleared BEFORE this request.
        _ = try? await perform(request)
    }
}

@MainActor
final class NativeFamilySession: ObservableObject {
    @Published private(set) var connectedUser: NativeFamilyIdentity?
    @Published private(set) var groups: [NativeFamilyGroup] = []
    @Published private(set) var busy = false
    @Published private(set) var message: String?
    @Published private(set) var shareResults: [String: NativeFamilyActivityReceipt] = [:]
    @Published private(set) var sharingKeys: Set<String> = []
    @Published private(set) var connectedAt: Date?
    // A self-declared adult-only pilot gate, NOT proof of guardian authority.
    // This has no persistence and cannot authorize minor/guardian participation.
    @Published private(set) var adultPilotAcknowledged = false

    private var currentAccount: NativeFamilyAccount?
    private let api: NativeFamilyAPI
    private var generation = UUID()

    init(api: NativeFamilyAPI = NativeFamilyAPI()) { self.api = api }

    var isConnected: Bool { currentAccount != nil }

    /// A real login is voluntary, never part of AppShell.onAppear. In-memory
    /// credentials are not written to learner progress, UserDefaults or files.
    func signIn(server: String, email: String, password: String,
                adultPilotConfirmed: Bool, speech: NativeSpeechSession) async {
        guard !busy && !isConnected else { return }
        // Age is self-attested, not verified. Until a backend-authoritative
        // guardian relationship exists, do not support connected minor use.
        guard adultPilotConfirmed else {
            message = NativeFamilyError.adultPilotOnly.errorDescription
            return
        }
        let token = generation
        busy = true
        message = nil
        do {
            let origin = try NativeFamilyOrigin(text: server)
            let account = try await api.signIn(origin: origin, email: email, password: password)
            guard token == generation, !Task.isCancelled else { return }
            try speech.connectAfterOptionalLogin(origin: account.origin.url,
                                                 bearerToken: account.token)
            currentAccount = account
            connectedUser = account.user
            groups = account.groups
            connectedAt = Date()
            adultPilotAcknowledged = true
            shareResults = [:]
            sharingKeys = []
        } catch {
            if token == generation {
                speech.disconnect()
                currentAccount = nil
                connectedUser = nil
                groups = []
                connectedAt = nil
                adultPilotAcknowledged = false
                shareResults = [:]
                sharingKeys = []
                message = (error as? LocalizedError)?.errorDescription ??
                    NativeFamilyError.unavailable.errorDescription
            }
        }
        if token == generation { busy = false }
    }

    func loadSummary(for group: NativeFamilyGroup) async throws -> NativeFamilySummary {
        guard adultPilotAcknowledged, let account = currentAccount,
              account.groups.contains(group) else { throw NativeFamilyError.notAuthorized }
        return try await api.summary(for: group, account: account)
    }

    /// Explicit user click only. Never auto-upload history after login,
    /// app startup, reconnect or offline return.
    func recentShareCandidates(in learner: LocalLearningStore) -> [LocalXPEvent] {
        guard adultPilotAcknowledged, currentAccount != nil, let connectedAt else { return [] }
        return NativeFamilyActivityGuard.candidates(
            events: learner.expedition.events, lessons: learner.lessons,
            regions: learner.regions, connectedAt: connectedAt)
    }

    func receipt(for event: LocalXPEvent, group: NativeFamilyGroup) -> NativeFamilyActivityReceipt? {
        shareResults[Self.shareKey(for: event, group: group)]
    }

    func isSharing(event: LocalXPEvent, group: NativeFamilyGroup) -> Bool {
        sharingKeys.contains(Self.shareKey(for: event, group: group))
    }

    static func shareKey(for event: LocalXPEvent, group: NativeFamilyGroup) -> String {
        String(group.id) + "|" + event.id
    }

    @discardableResult
    func share(eventID: String, group: NativeFamilyGroup,
               learner: LocalLearningStore) async throws -> NativeFamilyActivityReceipt {
        guard adultPilotAcknowledged, let account = currentAccount, let connectedAt,
              account.groups.contains(group) else {
            throw NativeFamilyError.notAuthorized
        }
        let candidates = NativeFamilyActivityGuard.candidates(
            events: learner.expedition.events, lessons: learner.lessons,
            regions: learner.regions, connectedAt: connectedAt)
        guard let selected = candidates.first(where: { $0.id == eventID }) else {
            throw NativeFamilyError.notShareable
        }
        let key = Self.shareKey(for: selected, group: group)
        if let existing = shareResults[key] { return existing }
        guard !sharingKeys.contains(key) else { throw NativeFamilyError.alreadySharing }
        let started = generation
        sharingKeys.insert(key)
        defer { sharingKeys.remove(key) }
        let result = try await api.shareActivity(event: selected, to: group, account: account)
        guard started == generation, !Task.isCancelled else {
            throw NativeFamilyError.cancelled
        }
        shareResults[key] = result
        return result
    }

    func signOut(speech: NativeSpeechSession) async {
        let account = currentAccount
        generation = UUID()  // invalidates any in-flight sign-in
        currentAccount = nil
        connectedUser = nil
        groups = []
        connectedAt = nil
        adultPilotAcknowledged = false
        sharingKeys = []
        shareResults = [:]
        busy = false
        message = nil
        speech.disconnect() // immediate in-memory secret wipe
        if let account { await api.logOut(account: account) }
    }
}
