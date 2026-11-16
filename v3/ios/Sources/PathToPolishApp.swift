import SwiftUI

@main
struct PathToPolishApp: App {
    @StateObject private var learner = LocalLearningStore()
    @StateObject private var onDevicePronunciation = NativeOnDevicePronunciation()

    var body: some Scene {
        WindowGroup {
            AppShell()
                .environmentObject(learner)
                .environmentObject(onDevicePronunciation)
        }
    }
}
