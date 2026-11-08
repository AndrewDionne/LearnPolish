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
        let payload = try XCTUnwrap(requests[0].httpBody)
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
}
