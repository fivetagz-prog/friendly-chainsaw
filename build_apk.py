#!/usr/bin/env python3
"""
Real APK Builder using Android SDK + Gradle
"""

import os
import sys
import shutil
import zipfile
import argparse
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

class RealAPKBuilder:
    def __init__(self, app_name, package_name, output_dir="/output"):
        self.app_name = app_name
        self.package_name = package_name
        self.package_path = package_name.replace(".", "/")
        self.project_name = app_name.replace(" ", "").replace("-", "")
        self.output_dir = Path(output_dir)
        self.build_dir = Path(tempfile.mkdtemp(prefix="apk_build_"))
        self.project_dir = self.build_dir / self.project_name
        
    def log(self, msg):
        print(f"[BUILD] {msg}")
        sys.stdout.flush()
        
    def create_project(self):
        self.log(f"Creating project: {self.project_name}")
        dirs = [
            self.project_dir / "app/src/main/java" / self.package_path,
            self.project_dir / "app/src/main/res/layout",
            self.project_dir / "app/src/main/res/values",
            self.project_dir / "app/src/main/res/mipmap-hdpi",
            self.project_dir / "app/src/main/res/mipmap-mdpi",
            self.project_dir / "app/src/main/res/mipmap-xhdpi",
            self.project_dir / "app/src/main/res/mipmap-xxhdpi",
            self.project_dir / "app/src/main/res/mipmap-xxxhdpi",
            self.project_dir / "app/src/main/assets/www",
            self.project_dir / "gradle/wrapper",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            
    def write_gradle_files(self):
        self.log("Writing Gradle configuration...")
        
        with open(self.project_dir / "build.gradle", "w") as f:
            f.write("""buildscript {
    repositories { google(); mavenCentral() }
    dependencies { classpath 'com.android.tools.build:gradle:8.1.0' }
}
allprojects { repositories { google(); mavenCentral() } }
""")
        
        with open(self.project_dir / "settings.gradle", "w") as f:
            f.write(f"include ':app'\nrootProject.name = '{self.project_name}'\n")
            
        with open(self.project_dir / "gradle.properties", "w") as f:
            f.write("org.gradle.jvmargs=-Xmx4096m -Dfile.encoding=UTF-8\nandroid.useAndroidX=true\n")
            
        with open(self.project_dir / "gradle/wrapper/gradle-wrapper.properties", "w") as f:
            f.write("""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.0-bin.zip
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
""")
            
        with open(self.project_dir / "app/build.gradle", "w") as f:
            f.write(f"""plugins {{ id 'com.android.application' }}
android {{
    namespace '{self.package_name}'
    compileSdk 34
    defaultConfig {{
        applicationId "{self.package_name}"
        minSdk 21
        targetSdk 34
        versionCode 1
        versionName "1.0.0"
    }}
    buildTypes {{
        release {{
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }}
    }}
    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }}
}}
dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.google.android.material:material:1.9.0'
    implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
    implementation 'androidx.webkit:webkit:1.8.0'
}}
android {{
    signingConfigs {{
        debug {{
            storeFile file("debug.keystore")
            storePassword "android"
            keyAlias "androiddebugkey"
            keyPassword "android"
        }}
    }}
    buildTypes {{
        release {{
            signingConfig signingConfigs.debug
        }}
    }}
}}
""")
        
        with open(self.project_dir / "app/proguard-rules.pro", "w") as f:
            f.write("# ProGuard\n")
            
    def write_manifest(self):
        self.log("Writing AndroidManifest.xml...")
        with open(self.project_dir / "app/src/main/AndroidManifest.xml", "w") as f:
            f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{self.package_name}">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.App"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".{self.project_name}Activity"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:exported="true"
            android:theme="@style/Theme.App.NoActionBar">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
""")
            
    def write_activity(self, source_type, content):
        self.log("Generating MainActivity...")
        
        if source_type == "url":
            load_code = f'webView.loadUrl("{content}");'
        elif source_type in ["html", "files"]:
            load_code = 'webView.loadUrl("file:///android_asset/www/index.html");'
        else:
            load_code = 'webView.loadUrl("about:blank");'
            
        with open(self.project_dir / f"app/src/main/java/{self.package_path}/{self.project_name}Activity.java", "w") as f:
            f.write(f"""package {self.package_name};

import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

public class {self.project_name}Activity extends AppCompatActivity {{
    private WebView webView;
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        webView = findViewById(R.id.webview);
        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setCacheMode(WebSettings.LOAD_DEFAULT);
        ws.setAllowFileAccess(true);
        ws.setAllowContentAccess(true);
        ws.setMediaPlaybackRequiresUserGesture(false);
        webView.setWebViewClient(new WebViewClient());
        webView.setWebChromeClient(new WebChromeClient());
        {load_code}
    }}
    @Override
    public void onBackPressed() {{
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }}
}}
""")
            
    def write_resources(self):
        self.log("Writing resources...")
        
        with open(self.project_dir / "app/src/main/res/layout/activity_main.xml", "w") as f:
            f.write("""<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout 
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">
    <WebView
        android:id="@+id/webview"
        android:layout_width="0dp"
        android:layout_height="0dp"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent" />
</androidx.constraintlayout.widget.ConstraintLayout>
""")
        
        with open(self.project_dir / "app/src/main/res/values/strings.xml", "w") as f:
            f.write(f'<resources><string name="app_name">{self.app_name}</string></resources>\n')
            
        with open(self.project_dir / "app/src/main/res/values/colors.xml", "w") as f:
            f.write("""<resources>
    <color name="purple_200">#FFBB86FC</color>
    <color name="purple_500">#FF6200EE</color>
    <color name="purple_700">#FF3700B3</color>
    <color name="teal_200">#FF03DAC5</color>
    <color name="teal_700">#FF018786</color>
    <color name="black">#FF000000</color>
    <color name="white">#FFFFFFFF</color>
</resources>
""")
            
        with open(self.project_dir / "app/src/main/res/values/themes.xml", "w") as f:
            f.write("""<resources>
    <style name="Theme.App" parent="Theme.MaterialComponents.DayNight.DarkActionBar">
        <item name="colorPrimary">@color/purple_500</item>
        <item name="colorPrimaryVariant">@color/purple_700</item>
        <item name="colorOnPrimary">@color/white</item>
        <item name="colorSecondary">@color/teal_200</item>
    </style>
    <style name="Theme.App.NoActionBar" parent="Theme.App">
        <item name="windowActionBar">false</item>
        <item name="windowNoTitle">true</item>
    </style>
</resources>
""")
            
    def create_icons(self, icon_path=None):
        self.log("Creating launcher icons...")
        sizes = {
            "mipmap-mdpi": 48,
            "mipmap-hdpi": 72,
            "mipmap-xhdpi": 96,
            "mipmap-xxhdpi": 144,
            "mipmap-xxxhdpi": 192,
        }
        
        for folder, size in sizes.items():
            if icon_path and os.path.exists(icon_path):
                img = Image.open(icon_path).convert("RGBA")
                img = img.resize((size, size), Image.LANCZOS)
            else:
                img = Image.new("RGBA", (size, size), (37, 99, 235, 255))
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size//2)
                except:
                    font = ImageFont.load_default()
                draw.text((size/2, size/2), self.app_name[0].upper(), fill=(255,255,255,255), font=font, anchor="mm")
                
            img.save(self.project_dir / f"app/src/main/res/{folder}/ic_launcher.png")
            
            mask = Image.new("L", (size, size), 0)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            round_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            round_img.paste(img, (0, 0), mask)
            round_img.save(self.project_dir / f"app/src/main/res/{folder}/ic_launcher_round.png")
            
    def copy_content(self, source_type, content, files_dir=None):
        if source_type == "html":
            self.log("Writing HTML to assets...")
            with open(self.project_dir / "app/src/main/assets/www/index.html", "w", encoding="utf-8") as f:
                f.write(content)
        elif source_type == "files" and files_dir:
            self.log(f"Copying files from {files_dir}...")
            target = self.project_dir / "app/src/main/assets/www"
            if os.path.isdir(files_dir):
                for item in os.listdir(files_dir):
                    s = os.path.join(files_dir, item)
                    d = os.path.join(target, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                        
    def build_apk(self):
        self.log("Starting Gradle build...")
        
        keystore_path = self.build_dir / "debug.keystore"
        if not keystore_path.exists():
            self.log("Creating debug keystore...")
            subprocess.run([
                "keytool", "-genkey", "-v",
                "-keystore", str(keystore_path),
                "-storepass", "android",
                "-alias", "androiddebugkey",
                "-keypass", "android",
                "-keyalg", "RSA",
                "-validity", "10000",
                "-dname", "CN=Android Debug,O=Android,C=US"
            ], check=True, capture_output=True)
            
        # Copy keystore into project
        shutil.copy2(keystore_path, self.project_dir / "app/debug.keystore")
        
        self.log("Running: ./gradlew assembleRelease")
        gradlew = self.project_dir / "gradlew"
        
        if not gradlew.exists():
            self.log("Setting up Gradle wrapper...")
            subprocess.run(
                ["gradle", "wrapper", "--gradle-version", "8.0"],
                cwd=self.project_dir,
                check=True,
                capture_output=True
            )
            
        result = subprocess.run(
            [str(gradlew), "assembleRelease"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            self.log("BUILD FAILED")
            print(result.stdout)
            print(result.stderr)
            return False
            
        self.log("Build successful!")
        return True
        
    def copy_output(self):
        apk_source = self.project_dir / "app/build/outputs/apk/release/app-release.apk"
        if apk_source.exists():
            apk_dest = self.output_dir / f"{self.project_name}.apk"
            shutil.copy2(apk_source, apk_dest)
            self.log(f"APK saved: {apk_dest}")
            
        zip_path = self.output_dir / f"{self.project_name}_project.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.project_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.project_dir.parent)
                    zf.write(file_path, arcname)
        self.log(f"Project ZIP saved: {zip_path}")
        
    def run(self, source_type, content, files_dir=None, icon_path=None):
        self.create_project()
        self.write_gradle_files()
        self.write_manifest()
        self.write_activity(source_type, content)
        self.write_resources()
        self.create_icons(icon_path)
        self.copy_content(source_type, content, files_dir)
        
        if self.build_apk():
            self.copy_output()
            self.log("✅ DONE")
        else:
            self.log("❌ Build failed")
            sys.exit(1)
            

def main():
    parser = argparse.ArgumentParser(description="Build real APK from HTML/URL/Files")
    parser.add_argument("--name", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--source", choices=["html", "url", "files"], required=True)
    parser.add_argument("--content", help="HTML string or URL")
    parser.add_argument("--files-dir", help="Directory for files source")
    parser.add_argument("--icon", help="Icon image path")
    parser.add_argument("--output", default="/output")
    args = parser.parse_args()
    
    builder = RealAPKBuilder(args.name, args.package, args.output)
    builder.run(args.source, args.content, args.files_dir, args.icon)

if __name__ == "__main__":
    main()

