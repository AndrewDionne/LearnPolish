import Foundation
import XCTest
@testable import PathToPolish

/// Simulator-only URLProtocol: no Azure, Groq, Neon, Render or microphone
/// network calls. Every counter starts at zero and there are NO retries.
private final class MockPrivateSpeechTransport: URLProtocol {
    static let lock = NSLock()
    static var responseCode = 200
    static var responseData = Data()
    static var attempts = 0

    static func reset(status: Int, data: Data) {
        lock.lock()
        responseCode = status
        responseData = data
        attempts = 0
        lock.unlock()
    }

    static func count() -> Int {
        lock.lock()
        defer { lock.unlock() }
        return attempts
    }

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        Self.lock.lock()
        Self.attempts += 1
        let status = Self.responseCode
        let data = Self.responseData
        Self.lock.unlock()
        guard let url = request.url,
              let response = HTTPURLResponse(url: url, statusCode: status,
                                             httpVersion: "HTTP/1.1",
                                             headerFields: ["Cache-Control":"no-store"]) else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() {}
}

@MainActor final class NativeSpeechTransportTests: XCTestCase {
    private func fixture() throws -> (LessonItem, NativeSpeechConnection, Data, NativeSpeechClient) {
        let lessons = try CatalogLoader.load()
        let item = try XCTUnwrap(lessons.flatMap(\.items).first { $0.pronunciationSegments != nil })
        let conn = try NativeSpeechConnection(
            origin: URL(string: "https://private-speech.invalid")!,
            sessionToken: String(repeating: "x", count: 40))
        let wave = try PronunciationWave.encode(samples:
            (0..<16_000).map { i in
                Int16((sin(2 * Double.pi * Double(i) * 260 / 16_000) * 3_000).rounded())
            })
        let conf = URLSessionConfiguration.ephemeral
        conf.protocolClasses = [MockPrivateSpeechTransport.self]
        let client = NativeSpeechClient(urlSession: URLSession(configuration: conf))
        return (item, conn, wave, client)
    }

    func testOneConsentedRequestToOnlyOriginalBlendedRoute() async throws {
        let (item, conn, wave, client) = try fixture()
        let segments = try XCTUnwrap(item.pronunciationSegments?.segments)
        let json = try JSONSerialization.data(withJSONObject: [
            "item_id": item.id,
            "status": "ok",
            "engine": "azure-whisper-blend-v1",
            "calibration": "experimental-uncalibrated",
            "combined": 67,
            "colourHints": [
                "method": "whisper-transcript-proxy-v1",
                "reference": item.polish,
                "segments": segments.map { ["polish": $0, "hint": "review"] }
            ]
        ])
        MockPrivateSpeechTransport.reset(status: 200, data: json)
        let response = try await client.assess(connection: conn, item: item,
                                               wav: wave, approveAzure: true,
                                               approveGroq: true)
        guard case .blend(let score, _) = response else {
            return XCTFail("Expected source-bound response")
        }
        XCTAssertEqual(score, 67)
        XCTAssertEqual(MockPrivateSpeechTransport.count(), 1)
    }

    func testNoConsentNeverStartsOneProviderOrNetworkRequest() async throws {
        let (item, conn, wave, client) = try fixture()
        MockPrivateSpeechTransport.reset(status: 200, data: Data())
        for (azure, groq) in [(false, false), (true, false), (false, true)] {
            do {
                _ = try await client.assess(connection: conn, item: item, wav: wave,
                                            approveAzure: azure, approveGroq: groq)
                XCTFail("Nonconsented upload was allowed")
            } catch let e as NativeSpeechError {
                XCTAssertEqual(e, .consentRequired)
            }
        }
        XCTAssertEqual(MockPrivateSpeechTransport.count(), 0)
    }

    func testDailyLimitAndClosedServiceHaveNoSilentRetryOrScore() async throws {
        let (item, conn, wave, client) = try fixture()
        for (status, expected) in [(429, NativeSpeechError.dailyLimit),
                                   (503, NativeSpeechError.unavailable),
                                   (401, NativeSpeechError.sessionExpired)] {
            MockPrivateSpeechTransport.reset(status: status, data: Data())
            do {
                _ = try await client.assess(connection: conn, item: item, wav: wave,
                                            approveAzure: true, approveGroq: true)
                XCTFail("Failed service must not yield a score")
            } catch let error as NativeSpeechError {
                XCTAssertEqual(error, expected)
            }
            XCTAssertEqual(MockPrivateSpeechTransport.count(), 1)
        }
    }

    func testSwappedReplyNeverDisplaysAnotherWordsGrade() async throws {
        let (item, conn, wave, client) = try fixture()
        let json = try JSONSerialization.data(withJSONObject: [
            "item_id": "other:0", "status": "inconclusive", "reason": "no_match"
        ])
        MockPrivateSpeechTransport.reset(status: 200, data: json)
        do {
            _ = try await client.assess(connection: conn, item: item, wav: wave,
                                        approveAzure: true, approveGroq: true)
            XCTFail("Foreign item response must be rejected even if inconclusive")
        } catch let error as NativeSpeechError {
            XCTAssertEqual(error, .invalidResponse)
        }
        XCTAssertEqual(MockPrivateSpeechTransport.count(), 1)
    }
}
