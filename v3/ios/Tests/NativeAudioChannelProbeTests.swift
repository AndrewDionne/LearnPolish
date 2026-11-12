import XCTest
@testable import PathToPolish

#if DEBUG
final class NativeAudioChannelProbeTests: XCTestCase {
    private func samples(_ wav: Data) -> ([Int16], [Int16]) {
        XCTAssertEqual(String(decoding: wav[0..<4], as: UTF8.self), "RIFF")
        XCTAssertEqual(String(decoding: wav[8..<12], as: UTF8.self), "WAVE")
        XCTAssertEqual(wav[22], 2, "diagnostic must be actual two-channel PCM")
        XCTAssertEqual(wav[34], 16, "16-bit PCM")
        func sample(_ offset: Int) -> Int16 {
            Int16(bitPattern: UInt16(wav[offset]) | (UInt16(wav[offset + 1]) << 8))
        }
        let count = (wav.count - 44) / 4
        let left = (0..<count).map { sample(44 + $0 * 4) }
        let right = (0..<count).map { sample(46 + $0 * 4) }
        return (left, right)
    }

    func testLeftToneHasNoSignalOnRight() {
        let (left, right) = samples(NativeAudioProbeTone.wav(.left, seconds: 0.1))
        XCTAssertTrue(left.contains { $0 != 0 })
        XCTAssertTrue(right.allSatisfy { $0 == 0 })
    }

    func testRightToneHasNoSignalOnLeft() {
        let (left, right) = samples(NativeAudioProbeTone.wav(.right, seconds: 0.1))
        XCTAssertTrue(left.allSatisfy { $0 == 0 })
        XCTAssertTrue(right.contains { $0 != 0 })
    }

    func testBothToneHasIdenticalNonzeroChannels() {
        let (left, right) = samples(NativeAudioProbeTone.wav(.both, seconds: 0.1))
        XCTAssertEqual(left, right)
        XCTAssertTrue(left.contains { $0 != 0 })
    }
}
#endif
