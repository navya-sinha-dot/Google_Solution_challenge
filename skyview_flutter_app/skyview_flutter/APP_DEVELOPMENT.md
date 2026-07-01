# 📱 SkyView Mobile App Development & Architecture

This document details the architecture, local offline-first capabilities, setup instructions, and best practices used in the SkyView Flutter Mobile Application.

---

## 🛠 Tech Stack & Core Dependencies

* **Framework**: Flutter (Dart)
* **State Management**: Riverpod (`flutter_riverpod`)
* **Local Database & Sync**: PowerSync (`powersync`) + SQLite (`sqlite3_flutter_libs`)
* **On-Device LLM Fallback**: Google Gemma 2B INT4 (`flutter_gemma`)
* **Http Client**: Dio (`dio`) for resumable downloads & Http (`http`) for standard API calls
* **Localization**: `easy_localization` (English, Hindi, and regional languages)

---

## 🏗 Key Architectural Components

### 1. Offline-First Synchronization (`PowerSyncService`)
To support full offline-first operations without app degradation, we use **PowerSync** backed by local SQLite storage.
* **Sync Schema**: Defines local tables for `chats`, `messages`, `mandi_rates`, and `profile`.
* **Caching Mechanisms**: Saves data (profiles, market rates, and advisor responses) on successful online fetches.
* **Local Fallback**: Automatically serves local SQLite entries if the user is offline or remote API requests fail.

### 2. On-Device Gemma Inference Fallback
When internet access is lost, the app routes conversation prompts and report generation tasks to an on-device local LLM:
* **Gemma 2B INT4**: A quantized version of Google's Gemma model designed to run efficiently on mobile GPUs.
* **Resumable Downloader**: Custom dio-based file manager that checks device memory (requires $\ge 4$ GB RAM) and downloads the model with partial range-resuming support.
* **Offline RAG**: Queries local SQLite databases for mandi rates and farmer profile context, injecting them into the Gemma prompt context to generate accurate offline answers.

---

## 📦 Setup & Installation

### Prerequisites
* Flutter SDK (`>= 3.4.0 < 4.0.0`)
* Android SDK (minimum API level 21)

### Steps

1. **Get Dependencies**:
   ```bash
   flutter pub get
   ```
2. **Local Package Override**:
   The `flutter_gemma` package is customized locally under `packages/flutter_gemma` to support dynamic on-device storage loading (rather than requiring rooted `/data/local/tmp` directories).
3. **Run Application**:
   ```bash
   flutter run
   ```
4. **Compile Release APK**:
   ```bash
   flutter build apk --release
   ```

---

## 🌟 Best Practices Used

* **Clean Architecture**: Separates UI screens (`lib/screens`), providers/controllers (`lib/services`), and model types.
* **Connection Resilience**: Using `connectivity_plus` to automatically detect connection changes and immediately bypass network timeouts when offline.
* **Resumable Downloads**: Downloading large files (1.44 GB model) via Dio `range` headers to prevent data waste on flaky network drops.
* **Proguard Bypasses**: Optimized release builds by creating robust Proguard exclusion rules (`android/app/proguard-rules.pro`) to prevent compiler minification drops for Java standard processing elements.
