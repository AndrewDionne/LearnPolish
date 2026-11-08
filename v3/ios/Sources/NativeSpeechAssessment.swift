import Foundation
import Combine

/// The V2 private-family server accepts Azure + Groq Whisper only with an
/// authenticated, email-verified user and TWO affirmative per-take consents.
/// No service URL, token or provider key is shipped with V3 or saved to disk.
struct NativeSpeechConnection {
    let endpoint: URL
    let sessionToken: String

    init(origin: URL, sessionToken: String) throws {
        guard let scheme = origin.scheme, scheme == "https",
              let host = origin.host, !host.isEmpty, !host.contains("*"),
              origin.user == nil, origin.password == nil, origin.query == nil,
              origin.fragment == nil,
              origin.path.isEmpty || origin.path == "/",
              (30...256).contains(sessionToken.count),
              sessionToken.rangeOfCharacter(from: .whitespacesAndNewlines) == nil else {
            throw NativeSpeechError.unavailable
        }
        endpoint = origin.appendingPathComponent("api/v2/family/speech/assess-blend")
        self.sessionToken = sessionToken
    }
}

enum NativeSpeechError: LocalizedError {
    case unavailable, consentRequired, invalidResponse, sessionExpired, dailyLimit, timeout, cancelled

    var errorDescription: String? {
        switch self {
        case .unavailable: return "Pronunciation checking is unavailable. You can still record, replay and continue."
        case .consentRequired: return "Allow both providers to receive this take before checking."
        case .invalidResponse: return "Pronunciation feedback was unavailable for this take."
        case .sessionExpired: return "The optional speech connection has expired. Local practice still works."
        case .dailyLimit: return "Today's free pronunciation assessment allowance has been reached."
        case .timeout: return "Pronunciation checking timed out. You can replay or try again."
        case .cancelled: return "Pronunciation checking was cancelled."
        }
    }
}

struct NativeColourPart: Equatable {
    enum Hint: String, Decodable { case close, review, focus, uncertain }
    let polish: String
    let hint: Hint
}
enum NativeSpeechFeedback: Equatable {
    case blend(score: Int, parts: [NativeColourPart])
    case inconclusive(String)
}

private struct SpeechReply: Decodable {
    let item_id: String
    let status: String
    let engine: String?
    let calibration: String?
    let combined: Int?
    let colourHints: Hints?
    let reason: String?
    struct Hints: Decodable {
        let method: String
        let reference: String
        let segments: [Part]
        struct Part: Decodable {
            let polish: String
            let hint: NativeColourPart.Hint
        }
    }
}

enum NativeSpeechValidation {
    /// All provider fields except exact source-bound feedback are discarded.
    /// An uncalibrated colour category is a transcript-difference hint, NOT
    /// a calibrated acoustic or per-syllable numerical measurement.
    static func decode(_ data: Data, item: LessonItem) throws -> NativeSpeechFeedback {
        guard let reply = try? JSONDecoder().decode(SpeechReply.self, from: data),
              reply.item_id == item.id else {
            throw NativeSpeechError.invalidResponse
        }
        if reply.status == "inconclusive" {
            let messages: [String: String] = [
                "no_match": "Speech could not be recognized reliably. Try again.",
                "canceled": "The provider could not assess this take.",
                "no_assessment": "There was not enough pronunciation evidence for a score.",
                "provider_inconclusive": "Pronunciation feedback was inconclusive.",
                "provider_unavailable": "Pronunciation checking is temporarily unavailable."
            ]
            return .inconclusive(messages[reply.reason ?? ""] ?? "Pronunciation feedback was inconclusive.")
        }
        guard reply.status == "ok",
              reply.engine == "azure-whisper-blend-v1",
              reply.calibration == "experimental-uncalibrated",
              let score = reply.combined, (0...100).contains(score),
              let hints = reply.colourHints,
              hints.method == "whisper-transcript-proxy-v1",
              hints.reference == item.polish,
              let sourceSegments = item.pronunciationSegments?.segments,
              sourceSegments.count >= 1, sourceSegments.count <= 32,
              hints.segments.count == sourceSegments.count,
              hints.segments.map(\.polish) == sourceSegments,
              sourceSegments.joined() == item.polish else {
            throw NativeSpeechError.invalidResponse
        }
        return .blend(score: score, parts: hints.segments.map {
            NativeColourPart(polish: $0.polish, hint: $0.hint)
        })
    }
}

/// One bounded private request. No automatic retries and no stored audio,
/// transcripts, response history, provider secrets or token persistence.
struct NativeSpeechClient {
    let urlSession: URLSession

    init(urlSession: URLSession = .shared) {
        self.urlSession = urlSession
    }

    static func makeRequest(connection: NativeSpeechConnection,
                            item: LessonItem, wav: Data,
                            approveAzure: Bool, approveGroq: Bool) throws -> URLRequest {
        guard approveAzure && approveGroq else { throw NativeSpeechError.consentRequired }
        guard !item.id.isEmpty, !item.polish.isEmpty,
              item.referenceReview != "practice_only",
              item.pronunciationSegments?.segments.joined() == item.polish else {
            throw NativeSpeechError.unavailable
        }
        try PronunciationWave.verify(wav)
        let boundary = "ptp-" + UUID().uuidString
        var body = Data()
        func append(_ text: String) { body.append(contentsOf: text.utf8) }
        func field(_ name: String, _ value: String) {
            append("--" + boundary + "\r\n")
            append("Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n")
            append(value + "\r\n")
        }
        field("item_id", item.id)
        field("approve_azure_audio_upload", "yes")
        field("approve_groq_audio_upload", "yes")
        append("--" + boundary + "\r\n")
        append("Content-Disposition: form-data; name=\"audio\"; filename=\"learner.wav\"\r\n")
        append("Content-Type: audio/wav\r\n\r\n")
        body.append(wav)
        append("\r\n--" + boundary + "--\r\n")

        var request = URLRequest(url: connection.endpoint,
                                 cachePolicy: .reloadIgnoringLocalCacheData,
                                 timeoutInterval: 45)
        request.httpMethod = "POST"
        request.setValue("Bearer " + connection.sessionToken, forHTTPHeaderField: "Authorization")
        request.setValue("multipart/form-data; boundary=" + boundary,
                         forHTTPHeaderField: "Content-Type")
        request.setValue("no-store", forHTTPHeaderField: "Cache-Control")
        request.httpBody = body
        return request
    }

    func assess(connection: NativeSpeechConnection, item: LessonItem,
                wav: Data, approveAzure: Bool, approveGroq: Bool) async throws -> NativeSpeechFeedback {
        let request = try Self.makeRequest(connection: connection, item: item, wav: wav,
                                           approveAzure: approveAzure, approveGroq: approveGroq)
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await urlSession.data(for: request)
        } catch {
            if Task.isCancelled { throw NativeSpeechError.cancelled }
            if let urlError = error as? URLError, urlError.code == .timedOut {
                throw NativeSpeechError.timeout
            }
            throw NativeSpeechError.unavailable
        }
        if Task.isCancelled { throw NativeSpeechError.cancelled }
        guard let http = response as? HTTPURLResponse else {
            throw NativeSpeechError.invalidResponse
        }
        switch http.statusCode {
        case 200:
            guard data.count <= 16_384 else { throw NativeSpeechError.invalidResponse }
            return try NativeSpeechValidation.decode(data, item: item)
        case 401, 403: throw NativeSpeechError.sessionExpired
        case 429: throw NativeSpeechError.dailyLimit
        case 503: throw NativeSpeechError.unavailable
        default: throw NativeSpeechError.invalidResponse
        }
    }
}

@MainActor final class NativeSpeechSession: ObservableObject {
    @Published private(set) var isConnected = false
    private var connection: NativeSpeechConnection?
    private let client: NativeSpeechClient

    init(client: NativeSpeechClient = NativeSpeechClient()) {
        self.client = client
    }

    /// Called ONLY after a separate, voluntary, verified family connection.
    /// Never invoked on first launch. Token remains in memory only.
    func connectAfterOptionalLogin(origin: URL, bearerToken: String) throws {
        let validated = try NativeSpeechConnection(origin: origin, sessionToken: bearerToken)
        connection = validated
        isConnected = true
    }

    func disconnect() {
        connection = nil
        isConnected = false
    }

    func assess(item: LessonItem, wav: Data,
                approveAzure: Bool, approveGroq: Bool) async throws -> NativeSpeechFeedback {
        guard let connection else { throw NativeSpeechError.unavailable }
        return try await client.assess(connection: connection, item: item, wav: wav,
                                       approveAzure: approveAzure, approveGroq: approveGroq)
    }
}
