import Foundation
import XCTest
@testable import PathToPolish

/// Local-only network fixture. These tests never reach a family account,
/// database, payment service or external speech provider.
private final class MockFamilyProtocol: URLProtocol {
    struct Reply {
        let status: Int
        let bytes: Data
    }
    private static let lock = NSLock()
    private static var replies: [String: Reply] = [:]
    private static var calls: [URLRequest] = []

    static func setup(_ fixtures: [String: Reply]) {
        lock.lock()
        replies = fixtures
        calls = []
        lock.unlock()
    }
    static func requests() -> [URLRequest] {
        lock.lock()
        defer { lock.unlock() }
        return calls
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.lock.lock()
        Self.calls.append(request)
        let response = Self.replies[request.url?.path ?? ""]
        Self.lock.unlock()
        let code = response?.status ?? 404
        guard let url = request.url,
              let http = HTTPURLResponse(url: url, statusCode: code,
                                          httpVersion: "HTTP/1.1",
                                          headerFields: ["Cache-Control":"no-store"]) else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }
        client?.urlProtocol(self, didReceive: http, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: response?.bytes ?? Data())
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

@MainActor final class NativeFamilyTests: XCTestCase {
    private let token = String(repeating: "v", count: 45)
    private let address = "https://private.example.org"

    private func json(_ object: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: object)
    }
    private func stub(status: Int = 200, _ object: [String: Any]) throws -> MockFamilyProtocol.Reply {
        MockFamilyProtocol.Reply(status: status, bytes: try json(object))
    }
    private func goodFixtures() throws -> [String: MockFamilyProtocol.Reply] {
        [
            "/api/v2/family/login": try stub([
                "token": token, "user": ["id": 17, "name": "Existing Learner"]
            ]),
            "/api/v2/family/me": try stub([
                "user": ["id": 17, "name": "Existing Learner", "email": "learner@example.org"],
                "families": [["id": 9, "name": "Household"]]
            ]),
            "/api/v2/family/groups/9/summary": try stub([
                "group": ["id":9,"name":"Household"],
                "members": [
                    ["id":17,"name":"Existing Learner","weekly_xp":30,
                     "active_days":2,"highest_tier":1,"team_xp":20],
                    ["id":18,"name":"Another Learner","weekly_xp":40,
                     "active_days":3,"highest_tier":2,"team_xp":35]
                ],
                "regions": [],
                "totals": ["weekly_xp":70, "regions_unlocked":0]
            ]),
            "/api/v2/family/logout": try stub(["ok":true])
        ]
    }
    private func environment(_ replies: [String: MockFamilyProtocol.Reply])
        -> (NativeFamilySession, NativeSpeechSession) {
        MockFamilyProtocol.setup(replies)
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [MockFamilyProtocol.self]
        let api = NativeFamilyAPI(session: URLSession(configuration: configuration))
        return (NativeFamilySession(api: api), NativeSpeechSession())
    }
    private func connect(_ family: NativeFamilySession, _ speech: NativeSpeechSession) async {
        await family.signIn(server: address, email: "learner@example.org",
                            password: "test-only-pass", speech: speech)
    }


    func testFamilyMapUsesOnlyVerifiedServerRegionGoals() async throws {
        var fixtures = try goodFixtures()
        fixtures["/api/v2/family/groups/9/summary"] = try stub([
            "group": ["id":9, "name":"Household"],
            "members": [
                ["id":17, "name":"Existing Learner", "weekly_xp":60,
                 "active_days":2, "highest_tier":1, "team_xp":50]
            ],
            "regions":[
                ["region":"mazowieckie", "earned":320, "target":300, "unlocked":true],
                ["region":"małopolskie", "earned":20, "target":350, "unlocked":false]
            ],
            "totals":["weekly_xp":60, "regions_unlocked":1]
        ])
        let (family, speech) = environment(fixtures)
        await connect(family, speech)
        let group = try XCTUnwrap(family.groups.first)
        let summary = try await family.loadSummary(for: group)
        XCTAssertEqual(summary.totals.regions_unlocked, 1)
        XCTAssertTrue(summary.regions.first?.unlocked == true)
        XCTAssertEqual(summary.regions.last?.earned, 20)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 3)
    }

    func testTamperedOrInconsistentServerRegionNeverRendersFamilyMap() async throws {
        for invalid in [
            ["region":"fake-region", "earned":10, "target":300, "unlocked":false],
            ["region":"mazowieckie", "earned":310, "target":300, "unlocked":false],
            ["region":"mazowieckie", "earned":-1, "target":300, "unlocked":false],
            ["region":"mazowieckie", "earned":10, "target":0, "unlocked":false]
        ] as [[String:Any]] {
            var fixtures = try goodFixtures()
            fixtures["/api/v2/family/groups/9/summary"] = try stub([
                "group": ["id":9, "name":"Household"],
                "members":[
                    ["id":17, "name":"Existing Learner", "weekly_xp":10,
                     "active_days":1, "highest_tier":1, "team_xp":10]
                ],
                "regions":[invalid],
                "totals":["weekly_xp":10, "regions_unlocked":0]
            ])
            let (family, speech) = environment(fixtures)
            await connect(family, speech)
            let group = try XCTUnwrap(family.groups.first)
            do {
                _ = try await family.loadSummary(for: group)
                XCTFail("Untrusted region data cannot appear in the family map")
            } catch let error as NativeFamilyError {
                XCTAssertEqual(error, .malformedResponse)
            }
            XCTAssertEqual(MockFamilyProtocol.requests().count, 3)
        }
    }

    func testFirstLaunchRequiresNoLoginAndMakesNoNetworkRequests() throws {
        let (family, speech) = environment(try goodFixtures())
        XCTAssertFalse(family.isConnected)
        XCTAssertFalse(speech.isConnected)
        XCTAssertNil(family.connectedUser)
        XCTAssertTrue(family.groups.isEmpty)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 0)
        let localFolder = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: localFolder) }
        let local = LocalLearningStore(storageURL: localFolder.appendingPathComponent("learner.json"))
        XCTAssertNil(local.catalogError)
        XCTAssertNotNil(local.nextLesson)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 0)
    }

    func testOnlyExplicitSecureHTTPSRootCanReceivePassword() throws {
        let accepted = try NativeFamilyOrigin(text: "https://private.example.org")
        XCTAssertEqual(accepted.route("login").absoluteString,
                       "https://private.example.org/api/v2/family/login")
        for input in ["http://private.example.org","https://other:password@private.example.org",
                      "https://private.example.org/steal","https://private.example.org/?t=1",
                      "https://private.example.org/#a","https://*.private.example.org",
                      "file:///etc/passwd"] {
            XCTAssertThrowsError(try NativeFamilyOrigin(text: input), input)
        }
    }

    func testVerifiedExistingLoginConnectsPrivateSpeechWithoutSharingXP() async throws {
        let (family, speech) = environment(try goodFixtures())
        await connect(family, speech)
        XCTAssertTrue(family.isConnected)
        XCTAssertTrue(speech.isConnected)
        XCTAssertEqual(family.connectedUser?.name, "Existing Learner")
        XCTAssertEqual(family.groups.map(\.name), ["Household"])
        let requests = MockFamilyProtocol.requests()
        XCTAssertEqual(requests.map { $0.url?.path ?? "" },
                       ["/api/v2/family/login", "/api/v2/family/me"])
        XCTAssertNil(requests[0].value(forHTTPHeaderField: "Authorization"))
        XCTAssertEqual(requests[1].value(forHTTPHeaderField: "Authorization"), "Bearer " + token)
        // URLSession may expose the POST payload as an HTTPBodyStream when a
        // URLProtocol test double intercepts it. Validate the exact request
        // constructor's JSON body rather than the stream representation.
        let origin = try NativeFamilyOrigin(text: address)
        let encoded = try JSONSerialization.data(withJSONObject: [
            "email": "learner@example.org", "password": "test-only-pass"
        ])
        let built = NativeFamilyAPI.request(origin: origin, route: "login",
                                            method: "POST", body: encoded)
        let payload = try XCTUnwrap(built.httpBody)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: payload) as? [String:String])
        XCTAssertEqual(json["email"], "learner@example.org")
        XCTAssertEqual(json["password"], "test-only-pass")
        XCTAssertFalse(requests[0].url!.absoluteString.contains("test-only-pass"))
        XCTAssertTrue(requests.allSatisfy { $0.httpShouldHandleCookies == false })
        XCTAssertTrue(requests.allSatisfy { $0.cachePolicy == .reloadIgnoringLocalCacheData })
        XCTAssertFalse(requests.contains { $0.url?.path.contains("/activity") == true })
    }

    func testRejectedLoginNeverConnectsSpeechOrCreatesAccount() async throws {
        var fixtures = try goodFixtures()
        fixtures["/api/v2/family/login"] = try stub(status: 401, ["error":"invalid_credentials"])
        let (family, speech) = environment(fixtures)
        await connect(family, speech)
        XCTAssertFalse(family.isConnected)
        XCTAssertFalse(speech.isConnected)
        XCTAssertEqual(family.message, NativeFamilyError.invalidCredentials.errorDescription)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 1)
    }

    func testEmailNotVerifiedAndRateLimitFailClosedWithoutSpeech() async throws {
        for (status, expected) in [(403, NativeFamilyError.verificationRequired),
                                   (429, NativeFamilyError.tooManyAttempts)] {
            var fixtures = try goodFixtures()
            fixtures["/api/v2/family/login"] = try stub(status: status, ["error":"no_session"])
            let (family, speech) = environment(fixtures)
            await connect(family, speech)
            XCTAssertFalse(family.isConnected)
            XCTAssertFalse(speech.isConnected)
            XCTAssertEqual(family.message, expected.errorDescription)
            XCTAssertEqual(MockFamilyProtocol.requests().count, 1)
        }
    }

    func testMismatchedVerifiedIdentityOrFakeTokenNeverConnects() async throws {
        var fixtures = try goodFixtures()
        fixtures["/api/v2/family/me"] = try stub([
            "user":["id": 19, "name":"Other Person", "email":"different@example.org"],
            "families":[]
        ])
        let (family, speech) = environment(fixtures)
        await connect(family, speech)
        XCTAssertFalse(family.isConnected)
        XCTAssertFalse(speech.isConnected)
        XCTAssertEqual(family.message, NativeFamilyError.malformedResponse.errorDescription)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 2)
    }

    func testReadOnlyServerAuthoritativeWeeklyScores() async throws {
        let (family, speech) = environment(try goodFixtures())
        await connect(family, speech)
        let group = try XCTUnwrap(family.groups.first)
        let result = try await family.loadSummary(for: group)
        XCTAssertEqual(result.group.id, 9)
        XCTAssertEqual(result.members.map(\.weekly_xp), [30,40])
        XCTAssertEqual(result.totals.weekly_xp, 70)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 3)
        do {
            _ = try await family.loadSummary(for: NativeFamilyGroup(id: 999, name: "Unknown"))
            XCTFail("Membership cannot be inferred from local group names")
        } catch let e as NativeFamilyError {
            XCTAssertEqual(e, .notAuthorized)
        }
        XCTAssertEqual(MockFamilyProtocol.requests().count, 3)
    }

    func testSignOutClearsBothMemorySessionsAndRevokesOnServer() async throws {
        let (family, speech) = environment(try goodFixtures())
        await connect(family, speech)
        XCTAssertTrue(speech.isConnected)
        await family.signOut(speech: speech)
        XCTAssertFalse(family.isConnected)
        XCTAssertFalse(speech.isConnected)
        XCTAssertNil(family.connectedUser)
        XCTAssertTrue(family.groups.isEmpty)
        let requests = MockFamilyProtocol.requests()
        XCTAssertEqual(requests.map { $0.url?.path ?? "" },
                       ["/api/v2/family/login", "/api/v2/family/me",
                        "/api/v2/family/logout"])
        XCTAssertEqual(requests.last?.value(forHTTPHeaderField: "Authorization"),
                       "Bearer " + token)
    }

    func testFamilyActivityNeverUploadsOnLoginOrLocalPracticeWithoutShare() async throws {
        var fixtures = try goodFixtures()
        fixtures["/api/v2/family/groups/9/activity"] = try stub(status: 201, [
            "accepted": true, "xp": 10, "expedition_xp": 10,
            "region": "mazowieckie", "target": 300
        ])
        let (family, speech) = environment(fixtures)
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: directory.appendingPathComponent("learner.json"))
        let lesson = try XCTUnwrap(learner.lessons.first(where: { $0.kind == "vocabulary" }))
        let item = try XCTUnwrap(lesson.items.first)
        learner.recordAttempt(item: item, mode: .learn, understood: true)
        XCTAssertTrue(family.recentShareCandidates(in: learner).isEmpty)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 0)
        await connect(family, speech)
        XCTAssertTrue(family.recentShareCandidates(in: learner).isEmpty,
                      "Old local XP must never be uploaded when connecting")
        learner.recordAttempt(item: item, mode: .listen, understood: true)
        XCTAssertEqual(family.recentShareCandidates(in: learner).count, 1)
        XCTAssertEqual(MockFamilyProtocol.requests().map { $0.url?.path ?? "" },
                       ["/api/v2/family/login", "/api/v2/family/me"])
    }

    func testExplicitSingleShareUsesOnlyThreeBackendFieldsAndAcknowledgedServerXP() async throws {
        var fixtures = try goodFixtures()
        fixtures["/api/v2/family/groups/9/activity"] = try stub(status: 201, [
            "accepted": true, "xp": 14, "expedition_xp": 7,
            "region": "mazowieckie", "target": 310
        ])
        let (family, speech) = environment(fixtures)
        await connect(family, speech)
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: directory.appendingPathComponent("learner.json"))
        let item = try XCTUnwrap(learner.lessons.first(where: { $0.kind == "vocabulary" })?.items.first)
        learner.recordAttempt(item: item, mode: .learn, understood: false)
        let event = try XCTUnwrap(family.recentShareCandidates(in: learner).first)
        let group = try XCTUnwrap(family.groups.first)
        let localXP = learner.expedition.totalXP
        let result = try await family.share(eventID: event.id, group: group, learner: learner)
        XCTAssertEqual(result, .credited(xp: 14, expeditionXP: 7))
        XCTAssertEqual(learner.expedition.totalXP, localXP,
                       "Server XP must never increase anonymous local XP")
        XCTAssertEqual(family.receipt(for: event, group: group), result)
        XCTAssertEqual(MockFamilyProtocol.requests().map { $0.url?.path ?? "" },
                       ["/api/v2/family/login", "/api/v2/family/me",
                        "/api/v2/family/groups/9/activity"])
        let origin = try NativeFamilyOrigin(text: address)
        let account = NativeFamilyAccount(origin: origin, token: token,
              user: NativeFamilyIdentity(id: 17, name: "Existing Learner", email: "learner@example.org"),
              groups: [group])
        let req = try NativeFamilyAPI.activityRequest(account: account, group: group, event: event)
        XCTAssertEqual(req.httpMethod, "POST")
        XCTAssertEqual(req.value(forHTTPHeaderField: "Authorization"), "Bearer " + token)
        let data = try XCTUnwrap(req.httpBody)
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String:String])
        XCTAssertEqual(Set(body.keys), Set(["item_id", "mode", "region"]))
        XCTAssertEqual(body["item_id"], event.itemID)
        XCTAssertEqual(body["mode"], event.mode.rawValue)
        XCTAssertEqual(body["region"], event.regionID)
        XCTAssertNil(body["xp"])
        XCTAssertNil(body["date"])
        XCTAssertNil(body["audio"])
        // Explicit repeat click returns the in-memory receipt without a request.
        let same = try await family.share(eventID: event.id, group: group, learner: learner)
        XCTAssertEqual(same, result)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 3)
    }

    func testAlreadyCreditedIsAcknowledgedWithoutAwardingClientXPOrRetry() async throws {
        var fixtures = try goodFixtures()
        fixtures["/api/v2/family/groups/9/activity"] = try stub([
            "accepted": false, "reason": "already_credited"
        ])
        let (family, speech) = environment(fixtures)
        await connect(family, speech)
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: directory.appendingPathComponent("learner.json"))
        let item = try XCTUnwrap(learner.lessons.first(where: { $0.kind == "vocabulary" })?.items.first)
        learner.recordAttempt(item: item, mode: .learn, understood: true)
        let event = try XCTUnwrap(family.recentShareCandidates(in: learner).first)
        let group = try XCTUnwrap(family.groups.first)
        let result = try await family.share(eventID: event.id, group: group, learner: learner)
        XCTAssertEqual(result, .alreadyCredited)
        XCTAssertEqual(MockFamilyProtocol.requests().count, 3)
        XCTAssertEqual(family.receipt(for: event, group: group), .alreadyCredited)
        await family.signOut(speech: speech)
        XCTAssertNil(family.receipt(for: event, group: group))
        XCTAssertTrue(family.recentShareCandidates(in: learner).isEmpty)
        XCTAssertFalse(speech.isConnected)
    }

    func testMissingMembershipAndMalformedReceiptFailClosed() async throws {
        var fixtures = try goodFixtures()
        fixtures["/api/v2/family/groups/9/activity"] = try stub([
            "accepted": true, "xp": 9999, "expedition_xp": 9999,
            "region": "unknown", "target": 0
        ])
        let (family, speech) = environment(fixtures)
        await connect(family, speech)
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let learner = LocalLearningStore(storageURL: directory.appendingPathComponent("learner.json"))
        let item = try XCTUnwrap(learner.lessons.first(where: { $0.kind == "vocabulary" })?.items.first)
        learner.recordAttempt(item: item, mode: .learn, understood: false)
        let event = try XCTUnwrap(family.recentShareCandidates(in: learner).first)
        let stranger = NativeFamilyGroup(id: 500, name: "Stranger")
        do {
            _ = try await family.share(eventID: event.id, group: stranger, learner: learner)
            XCTFail("Unknown group must never be submitted")
        } catch let error as NativeFamilyError { XCTAssertEqual(error, .notAuthorized) }
        XCTAssertEqual(MockFamilyProtocol.requests().count, 2)
        let group = try XCTUnwrap(family.groups.first)
        do {
            _ = try await family.share(eventID: event.id, group: group, learner: learner)
            XCTFail("Tampered server XP must not be displayed")
        } catch let error as NativeFamilyError { XCTAssertEqual(error, .malformedResponse) }
        XCTAssertEqual(MockFamilyProtocol.requests().count, 3)
        XCTAssertNil(family.receipt(for: event, group: group))
    }

    func testUTCBoundaryAndNewlyConnectedSessionFilterHistoricalActivity() throws {
        let lessons = try CatalogLoader.load()
        let items = try XCTUnwrap(lessons.first(where: { $0.kind == "vocabulary" })?.items)
        let regions = try PolandRegionCatalog.load()
        let now = Date(timeIntervalSince1970: 1_760_000_100)
        let start = now.addingTimeInterval(-120)
        func make(_ date: Date, _ itemID: String) -> LocalXPEvent {
            LocalXPEvent(id: "learn:" + itemID + ":2025-01-01", itemID: itemID,
                         mode: .learn, at: date, xp: 10, baseXP: 10,
                         expeditionXP: 10, tier: 1, regionID: "mazowieckie")
        }
        let valid = make(now.addingTimeInterval(-30), items[0].id)
        let beforeLogin = make(start.addingTimeInterval(-1), items[1].id)
        let future = make(now.addingTimeInterval(2), items[2].id)
        let priorUTCday = make(now.addingTimeInterval(-86_430), items[3].id)
        let corrupt = LocalXPEvent(id: "corrupt", itemID: items[4].id, mode: .learn,
                  at: now.addingTimeInterval(-10), xp: 100, baseXP: 100,
                  expeditionXP: 10, tier: 1, regionID: "mazowieckie")
        let candidates = NativeFamilyActivityGuard.candidates(
            events: [valid, beforeLogin, future, priorUTCday, corrupt],
            lessons: lessons, regions: regions, connectedAt: start, now: now)
        XCTAssertEqual(candidates.map(\.itemID), [valid.itemID])
    }
}
