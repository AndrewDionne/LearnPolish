import SwiftUI

/// A deliberately explicit replacement preview. Import never combines two
/// anonymous identities, XP ledgers or CloudKit histories behind the scenes.
struct LocalRestoreReviewSheet: View {
    let candidate: LocalRestorePreview
    let currentAttempts: Int
    let currentXP: Int
    let onRestore: () throws -> URL

    @Environment(\.dismiss) private var dismiss
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Progress to restore") {
                    LabeledContent("From", value: candidate.source)
                    LabeledContent("Saved", value:
                        candidate.archive.exportedAt.formatted(date: .abbreviated, time: .shortened))
                    LabeledContent("Practice attempts", value: "\(candidate.importedAttempts)")
                    LabeledContent("Personal XP", value: "\(candidate.importedXP)")
                }
                Section("Currently on this iPhone") {
                    LabeledContent("Practice attempts", value: "\(currentAttempts)")
                    LabeledContent("Personal XP", value: "\(currentXP)")
                }
                Section {
                    Text("Restoring replaces all local lesson attempts, reviews, positions and personal XP with this file. This is not a merge and will not link devices or family accounts.")
                    Text("A private, recoverable backup of the current profile is saved on this iPhone first. You can reopen it in Progress. Export a copy separately if you also want a file outside the app.")
                        .foregroundStyle(.secondary)
                }
                if let errorMessage {
                    Section {
                        Label(errorMessage, systemImage: "exclamationmark.triangle")
                            .foregroundStyle(.red)
                    }
                }
                Section {
                    Button("Replace local progress", role: .destructive) {
                        do {
                            _ = try onRestore()
                            dismiss()
                        } catch {
                            errorMessage = error.localizedDescription
                        }
                    }
                }
            }
            .navigationTitle("Review restoration")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
