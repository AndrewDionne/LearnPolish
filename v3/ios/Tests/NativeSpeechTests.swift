import XCTest
import AVFoundation
@testable import PathToPolish

@MainActor final class NativeSpeechTests: XCTestCase {
    private func sample() throws -> LessonItem {
        let lessons = try CatalogLoader.load()
        return try XCTUnwrap(lessons.flatMap(\.items).first {
            $0.pronunciationSegments != nil && $0.referenceReview != "practice_only"
        })
    }
    private func wav() throws -> Data {
        let samples = (0..<16_000).map { position -> Int16 in
            let sine = sin(2 * Double.pi * 240 * Double(position) / 16_000)
            return Int16((sine * 4_000).rounded())
        }
        return try PronunciationWave.encode(samples: samples)
    }
    private func reply(_ obj: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: obj)
    }
    private func blend(_ item: LessonItem, score: Int = 67,
                       id: String? = nil, reference: String? = nil) throws -> Data {
        let segments = try XCTUnwrap(item.pronunciationSegments?.segments)
        return try reply([
            "item_id": id ?? item.id,
            "status": "ok",
            "engine": "azure-whisper-blend-v1",
            "calibration": "experimental-uncalibrated",
            "combined": score,
            "colourHints": [
                "method": "whisper-transcript-proxy-v1",
                "reference": reference ?? item.polish,
                "segments": segments.map { ["polish": $0, "hint": "review"] }
            ],
            "rawTranscript": "private; should not reach native result",
            "audio_base64": "private; should never reach native result"
        ])
    }

    func testWavIsMono16KPCM16BoundedAndPrivate() throws {
        let data = try wav()
        XCTAssertEqual(data.count, 32_044)
        XCTAssertEqual(String(decoding: data.prefix(4), as: UTF8.self), "RIFF")
        XCTAssertEqual(String(decoding: data[8..<12], as: UTF8.self), "WAVE")
        XCTAssertEqual(data[22], 1)
        XCTAssertEqual(data[23], 0)
        XCTAssertEqual(data[24], 0x80) // 16000 sample rate little-endian
        XCTAssertEqual(data[25], 0x3e)
        XCTAssertEqual(data[34], 16)
        XCTAssertNoThrow(try PronunciationWave.verify(data))
        var changed = data
        changed[24] = 0
        XCTAssertThrowsError(try PronunciationWave.verify(changed))
    }

    func testWavRejectsSilenceClippingAndInvalidDuration() throws {
        XCTAssertThrowsError(try PronunciationWave.encode(samples: [Int16](repeating: 0, count: 16_000)))
        XCTAssertThrowsError(try PronunciationWave.encode(samples: [Int16](repeating: 32_767, count: 16_000)))
        XCTAssertThrowsError(try PronunciationWave.encode(samples: [Int16](repeating: 2_000, count: 4_000)))
        XCTAssertThrowsError(try PronunciationWave.encode(samples: [Int16](repeating: 2_000, count: 160_001)))
        var truncated = try wav()
        truncated.removeLast(2)
        XCTAssertThrowsError(try PronunciationWave.verify(truncated))
    }

    func testNativeDecodedFloatRecordingMakesUsablePrivateWav() throws {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString).appendingPathExtension("caf")
        defer { try? FileManager.default.removeItem(at: url) }
        let format = try XCTUnwrap(AVAudioFormat(standardFormatWithSampleRate: 44_100, channels: 1))
        let source = try AVAudioFile(forWriting: url, settings: format.settings)
        let pcm = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: format, frameCapacity: 44_100))
        pcm.frameLength = 44_100
        let channel = try XCTUnwrap(pcm.floatChannelData?[0])
        for i in 0..<44_100 {
            channel[i] = Float(sin(2 * Double.pi * 240 * Double(i) / 44_100) * 0.15)
        }
        try source.write(from: pcm)
        let output = try PronunciationWave.make(fromRecording: url)
        // AVAudioFile's converter can trim a few encoder priming frames.
        // Assert the actual PCM format and an approximately 1-second
        // playable capture, not bit-exact decoded length.
        XCTAssertGreaterThanOrEqual(output.count, 31_000)
        XCTAssertLessThanOrEqual(output.count, 32_044)
        XCTAssertNoThrow(try PronunciationWave.verify(output))
    }

    func testNoBackendIsContactedWithoutOptionalLogin() async throws {
        let item = try sample()
        let session = NativeSpeechSession()
        XCTAssertFalse(session.isConnected)
        do {
            _ = try await session.assess(item: item, wav: wav(),
                                         approveAzure: true, approveGroq: true)
            XCTFail("Never assess anonymously using family endpoint")
        } catch let e as NativeSpeechError {
            XCTAssertEqual(e, .unavailable)
        }
    }

    func testOriginAndBearerTokenMustPassPrivateSessionValidation() throws {
        let token = String(repeating: "a", count: 40)
        let good = try NativeSpeechConnection(origin: URL(string: "https://private.example.org")!,
                                              sessionToken: token)
        XCTAssertEqual(good.endpoint.absoluteString,
                       "https://private.example.org/api/v2/family/speech/assess-blend")
        for candidate in ["http://private.example.org", "https://private.example.org/extra",
                          "https://someone:password@private.example.org",
                          "https://private.example.org/?token=abc",
                          "https://*.example.org"] {
            XCTAssertThrowsError(try NativeSpeechConnection(origin: URL(string: candidate)!,
                                                              sessionToken: token))
        }
        XCTAssertThrowsError(try NativeSpeechConnection(
            origin: URL(string: "https://private.example.org")!, sessionToken: "short"))
    }

    func testPerTakeProviderConsentAndExactMultipartFields() throws {
        let item = try sample()
        let source = try wav()
        let secret = String(repeating: "b", count: 40)
        let connection = try NativeSpeechConnection(origin: URL(string: "https://private.example.org")!,
                                                     sessionToken: secret)
        XCTAssertThrowsError(try NativeSpeechClient.makeRequest(
            connection: connection, item: item, wav: source,
            approveAzure: false, approveGroq: true))
        XCTAssertThrowsError(try NativeSpeechClient.makeRequest(
            connection: connection, item: item, wav: source,
            approveAzure: true, approveGroq: false))
        let request = try NativeSpeechClient.makeRequest(
            connection: connection, item: item, wav: source,
            approveAzure: true, approveGroq: true)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url, connection.endpoint)
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer " + secret)
        XCTAssertEqual(request.cachePolicy, .reloadIgnoringLocalCacheData)
        XCTAssertEqual(request.timeoutInterval, 45)
        let bytes = try XCTUnwrap(request.httpBody)
        XCTAssertTrue(bytes.count >= source.count)
        let prefix = String(decoding: bytes.prefix(500), as: UTF8.self)
        XCTAssertTrue(prefix.contains("name=\"item_id\""))
        XCTAssertTrue(prefix.contains(item.id))
        XCTAssertTrue(prefix.contains("name=\"approve_azure_audio_upload\"\r\n\r\nyes"))
        XCTAssertTrue(prefix.contains("name=\"approve_groq_audio_upload\"\r\n\r\nyes"))
        XCTAssertTrue(prefix.contains("filename=\"learner.wav\""))
        XCTAssertTrue(prefix.contains("Content-Type: audio/wav"))
        XCTAssertFalse(prefix.contains("groq_api_key"))
    }

    func testExactSourceBoundBlendedColoursAndOnlyOneScore() throws {
        let item = try sample()
        let result = try NativeSpeechValidation.decode(blend(item), item: item)
        guard case .blend(let score, let parts) = result else {
            return XCTFail("Expected blended provider estimate")
        }
        XCTAssertEqual(score, 67)
        XCTAssertEqual(parts.map(\.polish), item.pronunciationSegments?.segments)
        XCTAssertEqual(parts.map(\.hint), Array(repeating: .review, count: parts.count))
        XCTAssertFalse(String(describing: result).contains("private"))
    }

    func testMismatchedOriginalItemOrSegmentMustNeverShowWrongWord() throws {
        let item = try sample()
        XCTAssertThrowsError(try NativeSpeechValidation.decode(
            blend(item, id: "other:0"), item: item))
        XCTAssertThrowsError(try NativeSpeechValidation.decode(
            blend(item, reference: "different word"), item: item))
        XCTAssertThrowsError(try NativeSpeechValidation.decode(
            blend(item, score: 101), item: item))
        let wrongEngine = try reply(["item_id":item.id,"status":"ok",
                                     "engine":"azure-pl-PL-scripted",
                                     "calibration":"uncalibrated",
                                     "scores":["accuracy":84]])
        XCTAssertThrowsError(try NativeSpeechValidation.decode(wrongEngine, item: item))
        var data = try XCTUnwrap(JSONSerialization.jsonObject(with: blend(item)) as? [String:Any])
        var hints = try XCTUnwrap(data["colourHints"] as? [String:Any])
        var segments = try XCTUnwrap(hints["segments"] as? [[String:Any]])
        segments[0]["polish"] = "not original"
        hints["segments"] = segments
        data["colourHints"] = hints
        XCTAssertThrowsError(try NativeSpeechValidation.decode(reply(data), item: item))
    }

    func testInconclusiveCannotBecomeZeroOrExposeProviderDetails() throws {
        let item = try sample()
        let response = try reply(["item_id":item.id, "status":"inconclusive",
                                  "reason":"PRIVATE_ERROR_WITH_TRANSCRIPT",
                                  "rawTranscript":"secret source"])
        let result = try NativeSpeechValidation.decode(response, item: item)
        guard case .inconclusive(let reason) = result else {
            return XCTFail("Inconclusive must never become a score")
        }
        XCTAssertFalse(reason.contains("PRIVATE"))
        XCTAssertFalse(reason.contains("secret"))
    }

    func testDisconnectedSessionRequiresNoOnboarding() throws {
        let session = NativeSpeechSession()
        XCTAssertFalse(session.isConnected)
        XCTAssertThrowsError(try session.connectAfterOptionalLogin(
            origin: URL(string: "http://example.org")!, bearerToken: "invalid"))
        XCTAssertFalse(session.isConnected)
        session.disconnect()
        XCTAssertFalse(session.isConnected)
    }
}
