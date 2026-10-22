package cl.arichard.descargador.util;

import android.content.Context;
import android.media.MediaScannerConnection;
import android.os.Build;
import android.os.Environment;
import java.io.File;

public class StorageUtil {

    public static File getDownloadDir(Context context) {
        // 1. Try public Download/Descargador
        try {
            File publicDownloads = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
            File descargadorDir = new File(publicDownloads, "Descargador");
            if (!descargadorDir.exists()) {
                descargadorDir.mkdirs();
            }
            if (descargadorDir.exists() && descargadorDir.canWrite()) {
                File probe = new File(descargadorDir, ".probe_" + System.currentTimeMillis());
                if (probe.createNewFile()) {
                    probe.delete();
                    return descargadorDir;
                }
            }
        } catch (Exception ignored) {}

        // 2. Try App External Music Dir (guaranteed to always work with 0 permissions on Android 10, 11, 12, 13, 14, 15)
        try {
            File extMusic = context.getExternalFilesDir(Environment.DIRECTORY_MUSIC);
            if (extMusic != null) {
                if (!extMusic.exists()) extMusic.mkdirs();
                if (extMusic.exists() && extMusic.canWrite()) {
                    return extMusic;
                }
            }
        } catch (Exception ignored) {}

        // 3. Fallback to internal files
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
