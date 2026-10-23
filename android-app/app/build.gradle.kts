plugins {
    id("com.android.application")
    id("com.google.gms.google-services")
}

android {
    namespace = "cl.arichard.descargador"
    compileSdk = 36

    defaultConfig {
        applicationId = "cl.arichard.descargador"
        minSdk = 24
        targetSdk = 29
        versionCode = 5
        versionName = "2.2.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a") }
    }

    buildTypes {
        create("preview") {
            initWith(getByName("debug"))
            applicationIdSuffix = ".pruebas"
            versionNameSuffix = "-pruebas"
            matchingFallbacks += listOf("debug")
        }
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    packaging { jniLibs { useLegacyPackaging = true } }
    testOptions { unitTests { isIncludeAndroidResources = true } }
    testBuildType = "preview"
    // Se distribuye como APK. La política de target de Google Play se informa como aviso.
    lint { warning += "ExpiredTargetSdkVersion" }
}

dependencies {
    implementation(platform("com.google.firebase:firebase-bom:35.0.2"))
    implementation("com.google.firebase:firebase-auth")
    implementation("com.google.firebase:firebase-firestore")
    implementation("androidx.credentials:credentials:1.3.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.3.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.uiautomator:uiautomator:2.3.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.robolectric:robolectric:4.16")
    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("com.google.android.material:material:1.13.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.media:media:1.7.0")
    implementation("io.github.junkfood02.youtubedl-android:library:0.18.1")
    implementation("io.github.junkfood02.youtubedl-android:ffmpeg:0.18.1")
}

tasks.withType<JavaCompile>().configureEach {
    options.encoding = "UTF-8"
}
