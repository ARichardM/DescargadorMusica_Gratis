package cl.arichard.descargador.util;

import android.content.Context;
import android.media.MediaScannerConnection;
import android.os.Build;
import android.os.Environment;
import java.io.File;

public class StorageUtil {

    public static File getDownloadDir(Context context) {
        // App-specific external storage works without broad filesystem access.
        try {
            File extMusic = context.getExternalFilesDir(Environment.DIRECTORY_MUSIC);
            if (extMusic != null) {
                if (!extMusic.exists()) extMusic.mkdirs();
                if (extMusic.exists() && extMusic.canWrite()) {
                    return extMusic;
                }
            }
        } catch (Exception ignored) {}

        // Fallback to internal storage.
        File internal = new File(context.getFilesDir(), "Music");
        if (!internal.exists()) internal.mkdirs();
        return internal;
    }

    public static void scanFile(Context context, File file) {
        if (file == null || !file.exists()) return;
        try {
            MediaScannerConnection.scanFile(
                context.getApplicationContext(),
                new String[]{file.getAbsolutePath()},
                null,
                (path, uri) -> {}
            );
        } catch (Exception ignored) {}
    }
}
