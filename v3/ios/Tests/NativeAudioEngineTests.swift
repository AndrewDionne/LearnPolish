import AVFoundation
import XCTest
@testable import PathToPolish

@MainActor final class NativeAudioEngineTests: XCTestCase {
    func testReferencePlaybackPreparesOnAudioQueueAndReturnsToMain() async throws {
        let lesson = try XCTUnwrap(CatalogLoader.load().first(where: { $0.items.contains { $0.audio != nil } }))
        let item = try XCTUnwrap(lesson.items.first(where: { $0.audio != nil }))
        let file = try XCTUnwrap(AudioFiles.referenceURL(for: try XCTUnwrap(item.audio)))
        let onMain = expectation(description: "Playback preparation calls back on main")
        let engine = NativeAudioEngine(sessionSetup: { mode in
            XCTAssertFalse(Thread.isMainThread,
                           "AVAudioSession configuration must never block SwiftUI")
            guard case .playback = mode else {
                return XCTFail("Reference playback must not request microphone session")
            }
        })
        engine.play(file, rate: 0.75) { _ in
            XCTAssertTrue(Thread.isMainThread)
            onMain.fulfill()
        }
        await fulfillment(of: [onMain], timeout: 10)
        engine.stopPlayback()
    }

    func testRecordingActivationRunsOffMainAndFailureDoesNotClaimRecording() async {
        let started = expectation(description: "Failed recording callback")
        let engine = NativeAudioEngine(sessionSetup: { mode in
            XCTAssertFalse(Thread.isMainThread)
            guard case .recording = mode else {
                return XCTFail("Recording must request recording session")
            }
            throw NSError(domain: "SimulatedAudioSession", code: 99)
        })
        let file = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString + ".m4a")
        engine.startRecording(to: file, started: { success in
            XCTAssertTrue(Thread.isMainThread)
            XCTAssertFalse(success, "Failed audio session cannot mark a take as captured")
            started.fulfill()
        }, stoppedAutomatically: { _ in
            XCTFail("Failed recording must never fire a ten-second finish")
        })
        await fulfillment(of: [started], timeout: 10)
        engine.discard(file: file)
    }

    func testAudioPreparationIsAsynchronousInsteadOfBlockingTapHandler() async throws {
        let entered = expectation(description: "Background setup started")
        let completed = expectation(description: "Background setup finished")
        let gate = DispatchSemaphore(value: 0)
        let engine = NativeAudioEngine(sessionSetup: { _ in
            XCTAssertFalse(Thread.isMainThread)
            entered.fulfill()
            _ = gate.wait(timeout: .now() + 5)
            throw NSError(domain: "SimulatedUnavailableAudioHardware", code: 50)
        })
        let file = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString + ".m4a")
        // If the UI waited for setActive this call would block until gate
        // opens. It must return immediately so the test can open the gate.
        engine.play(file, rate: 1) { success in
            XCTAssertFalse(success)
            completed.fulfill()
        }
        await fulfillment(of: [entered], timeout: 5)
        gate.signal()
        await fulfillment(of: [completed], timeout: 5)
        engine.discard(file: file)
    }
}
