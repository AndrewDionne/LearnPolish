import SwiftUI

/// Connection is voluntary. It never blocks first words, library, offline
/// playback, local Speak or personal progress; no new identity is provisioned.
struct NativeFamilyAccountScreen: View {
    @EnvironmentObject private var family: NativeFamilySession
    @EnvironmentObject private var speech: NativeSpeechSession

    @State private var server = ""
    @State private var email = ""
    @State private var password = ""

    var body: some View {
        Form {
            if let user = family.connectedUser {
                Section("Connected") {
                    LabeledContent("Account", value: user.name)
                    Text("Connected for this app session. Your local learning history remains separate.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                if !family.groups.isEmpty {
                    Section("Family groups") {
                        ForEach(family.groups) { group in
                            NavigationLink {
                                NativeFamilyGroupScreen(group: group)
                            } label: {
                                Label(group.name, systemImage: "person.2")
                            }
                        }
                    }
                } else {
                    Section("Family groups") {
                        Text("No groups linked to this account.")
                            .foregroundStyle(.secondary)
                    }
                }
                Section("Privacy") {
                    Text("No recorded voice is uploaded simply because you signed in. Each pronunciation check requires a new approval for both Azure and Groq.")
                        .font(.footnote).foregroundStyle(.secondary)
                    Text("Local progress and personal XP are not automatically shared with your family group.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Section {
                    Button("Sign out") {
                        Task { await family.signOut(speech: speech) }
                    }
                }
            } else {
                Section {
                    Text("Learning does not require an account. Connect only if you want to use your existing private family group or optional speech assessment.")
                        .foregroundStyle(.secondary)
                    TextField("Private family service URL", text: $server)
                        .textContentType(.URL)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    TextField("Email", text: $email)
                        .textContentType(.username)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Password", text: $password)
                        .textContentType(.password)
                    Button {
                        let attemptedPassword = password
                        password = ""
                        Task {
                            await family.signIn(server: server, email: email,
                                                password: attemptedPassword, speech: speech)
                        }
                    } label: {
                        if family.busy {
                            ProgressView("Connecting")
                        } else {
                            Text("Connect existing account")
                        }
                    }
                    .disabled(family.busy || server.isEmpty || email.isEmpty || password.isEmpty)
                } header: {
                    Text("Optional family connection")
                } footer: {
                    Text("Only existing verified accounts are supported. A secure HTTPS family service is required. Sign-in does not upload practice or microphone audio.")
                }
                if let message = family.message {
                    Section {
                        Label(message, systemImage: "info.circle")
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .navigationTitle("Family")
    }
}

/// Server-authoritative weekly results; never infer group XP from the local
/// expedition, which has deliberately different unshared identity.
private struct NativeFamilyGroupScreen: View {
    let group: NativeFamilyGroup
    @EnvironmentObject private var family: NativeFamilySession

    @State private var summary: NativeFamilySummary?
    @State private var loading = false
    @State private var errorMessage: String?

    var body: some View {
        List {
            if !family.isConnected {
                Text("Family session closed. Offline learning is still available.")
                    .foregroundStyle(.secondary)
            } else if let summary {
                Section("This week") {
                    LabeledContent("Group XP", value: String(summary.totals.weekly_xp))
                    LabeledContent("Regions unlocked", value: String(summary.totals.regions_unlocked))
                }
                Section("Group members") {
                    ForEach(summary.members) { member in
                        HStack {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(member.name)
                                Text("\(member.active_days) active days")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Text("\(member.weekly_xp) XP")
                                .font(.subheadline.monospacedDigit())
                        }
                    }
                }
            } else if loading {
                ProgressView("Loading group")
            } else if let errorMessage {
                Text(errorMessage).foregroundStyle(.secondary)
            }
        }
        .navigationTitle(group.name)
        .task(id: group.id) {
            await refresh()
        }
        .refreshable {
            await refresh()
        }
        .onChange(of: family.isConnected) { _, connected in
            if !connected {
                summary = nil
                loading = false
                errorMessage = nil
            }
        }
    }

    private func refresh() async {
        guard family.isConnected else {
            summary = nil
            loading = false
            errorMessage = nil
            return
        }
        loading = true
        errorMessage = nil
        do {
            let result = try await family.loadSummary(for: group)
            guard family.isConnected, !Task.isCancelled else { return }
            summary = result
        } catch {
            guard !Task.isCancelled else { return }
            summary = nil
            errorMessage = (error as? LocalizedError)?.errorDescription ??
                NativeFamilyError.unavailable.errorDescription
        }
        loading = false
    }
}
