import XCTest
@testable import PathToPolish

final class NativeOnDevicePronunciationTests: XCTestCase {
    func testRealRecognizedPolishProducesExactColouredSource() {
        let result = NativePronunciationTextAlignment.assess(
            reference: "Dzień dobry", recognized: "DZIEŃ DOBRY.",
            sourceSegments: ["Dzień", " ", "do", "bry"])
        guard case .onDeviceRecognition(let score, let parts) = result else {
            return XCTFail("Only a real transcript may produce feedback")
        }
        XCTAssertEqual(score, 100)
        XCTAssertEqual(parts.map(\.polish).joined(), "Dzień dobry")
        XCTAssertEqual(parts.map(\.hint), [.close, .uncertain, .close, .close])
    }

    func testMisrecognizedWordReducesScoreWithoutFabricatingSourceLetters() {
        let result = NativePronunciationTextAlignment.assess(
            reference: "Dzień dobry", recognized: "dzień dory",
            sourceSegments: ["Dzień", " ", "do", "bry"])
        guard case .onDeviceRecognition(let score, let parts) = result else {
            return XCTFail("Expected genuine mismatched transcription")
        }
        XCTAssertLessThan(score, 100)
        XCTAssertEqual(parts.map(\.polish).joined(), "Dzień dobry")
        XCTAssertEqual(parts[0].hint, .close)
        XCTAssertNotEqual(parts[3].hint, .close)
    }

    func testBlankOrPunctuationOnlyTranscriptionDoesNotCreateScore() {
        let result = NativePronunciationTextAlignment.assess(
            reference: "Tak", recognized: "  !! ", sourceSegments: ["Ta", "k"])
        guard case .inconclusive = result else {
            return XCTFail("No speech recognized must never generate a score")
        }
    }

    func testPolishDiacriticsRemainDistinct() {
        XCTAssertEqual(NativePronunciationTextAlignment.comparable("ŻÓŁĆ"),
                       Array("żółć"))
        XCTAssertNotEqual(NativePronunciationTextAlignment.comparable("zolc"),
                          NativePronunciationTextAlignment.comparable("żółć"))
    }

    func testMissingAuthoredSegmentsShowOnlyOriginalWords() {
        let result = NativePronunciationTextAlignment.assess(
            reference: "Dzień dobry", recognized: "dzień dobry",
            sourceSegments: nil)
        guard case .onDeviceRecognition(let score, let parts) = result else {
            return XCTFail("Expected local transcript agreement")
        }
        XCTAssertEqual(score, 100)
        XCTAssertEqual(parts.map(\.polish).joined(), "Dzień dobry")
        XCTAssertEqual(parts.count, 3)
    }
}
