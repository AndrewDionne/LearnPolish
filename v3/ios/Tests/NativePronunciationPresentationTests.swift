import XCTest
@testable import PathToPolish

@MainActor final class NativePronunciationPresentationTests: XCTestCase {
    func testExactOriginalSegmentsProduceOneOverallScoreAndDistinctHints() {
        let result = NativePronunciationPresentation(
            polish: "Dzień dobry",
            feedback: .blend(score: 67, parts: [
                NativeColourPart(polish: "Dzień", hint: .close),
                NativeColourPart(polish: " ", hint: .uncertain),
                NativeColourPart(polish: "do", hint: .review),
                NativeColourPart(polish: "bry", hint: .focus)
            ]))
        XCTAssertEqual(result?.score, 67)
        XCTAssertEqual(result?.segments.map(\.polish).joined(), "Dzień dobry")
        XCTAssertEqual(result?.segments.map(\.hint),
                       [.close, .uncertain, .review, .focus])
    }

    func testNoAssessmentInconclusiveAndMismatchedWordsNeverProduceColours() {
        XCTAssertNil(NativePronunciationPresentation(
            polish: "Tak", feedback: nil))
        XCTAssertNil(NativePronunciationPresentation(
            polish: "Tak", feedback: .inconclusive("Try again.")))
        XCTAssertNil(NativePronunciationPresentation(
            polish: "Tak", feedback: .blend(score: 67, parts: [
                NativeColourPart(polish: "Nie", hint: .focus)
            ])))
        XCTAssertNil(NativePronunciationPresentation(
            polish: "Tak", feedback: .blend(score: 101, parts: [
                NativeColourPart(polish: "Tak", hint: .close)
            ])))
    }

    func testRealZeroAndHundredRemainDistinctFromMissingProviderEvidence() {
        let token = [NativeColourPart(polish: "Tak", hint: .review)]
        XCTAssertEqual(NativePronunciationPresentation(
            polish: "Tak", feedback: .blend(score: 0, parts: token))?.score, 0)
        XCTAssertEqual(NativePronunciationPresentation(
            polish: "Tak", feedback: .blend(score: 100, parts: token))?.score, 100)
        XCTAssertNil(NativePronunciationPresentation(polish: "Tak", feedback: nil))
    }
}
