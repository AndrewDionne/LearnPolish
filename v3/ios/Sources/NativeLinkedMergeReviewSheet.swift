import SwiftUI

/// Manual, user-confirmed merge of two copies of the SAME anonymous learner.
/// The initial explicit Restore/transfer links a second device's learner
/// identity. This screen does not connect accounts, CloudKit or family groups.
struct NativeLinkedMergeReviewSheet: View {
    let review: NativeLinkedDevicePreview
    let currentXP: Int
    let onCombine: () throws -> URL

    @Environment(\.dismiss) private var dismiss
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Linked-device history") {
                    LabeledContent("This iPhone's attempts",
                                   value: "\(review.plan.originalEventCount)")
                    LabeledContent("Imported device's attempts",
                                   value: "\(review.plan.incomingEventCount)")
                    LabeledContent("Unique merged attempts",
                                   value: "\(review.plan.mergedEventCount)")
                    LabeledContent("New attempts from file",
                                   value: "\(review.plan.newEvents)")
                }
                Section("Reconciled personal XP") {
                    LabeledContent("Currently on this iPhone", value: "\(currentXP)")
                    LabeledContent("After UTC-day deduplication",
                                   value: "\(review.plan.mergedEffortXP)")
                    LabeledContent("Regional contribution",
                                   value: "\(review.plan.mergedRegionXP)")
                    Text("Cross-device XP uses one reward per original item, practice mode and UTC date. It may differ from previously shown phone-local XP.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Section("Before combining") {
                    Text("Only two copies of the same deliberately transferred anonymous profile may be combined. Independent learners, incomplete older journals and missing historical regions cannot be joined.")
                    Text("This replaces this iPhone's review history and personal XP with a source-verified calculation. This iPhone's navigation, tourist position and selected Poland region remain local.")
                        .foregroundStyle(.secondary)
                    Text("A private, recoverable copy of your current profile will be saved before any changes. It does not change your family scores or use iCloud.")
                        .foregroundStyle(.secondary)
                }
                if let errorMessage {
                    Section {
                        Label(errorMessage, systemImage: "exclamationmark.triangle")
                            .foregroundStyle(.red)
                    }
                }
                Section {
                    Button("Combine on this iPhone", role: .destructive) {
                        do {
                            _ = try onCombine()
                            dismiss()
                        } catch {
                            errorMessage = error.localizedDescription
                        }
                    }
                }
            }
            .navigationTitle("Review device merge")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
    }
}
