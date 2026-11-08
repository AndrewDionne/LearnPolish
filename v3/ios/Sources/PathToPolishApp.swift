import SwiftUI

@main
struct PathToPolishApp: App {
    @StateObject private var learner = LocalLearningStore()
    // In-memory only. No implicit login or remote connection at first launch.
    @StateObject private var speech = NativeSpeechSession()

    var body: some Scene {
        WindowGroup {
            AppShell()
                .environmentObject(learner)
                .environmentObject(speech)
        }
    }
}
