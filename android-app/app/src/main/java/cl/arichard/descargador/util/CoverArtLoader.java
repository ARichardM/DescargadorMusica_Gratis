package cl.arichard.descargador.util;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.media.MediaMetadataRetriever;
import android.os.Handler;
import android.os.Looper;
import android.util.LruCache;
import android.widget.ImageView;
import cl.arichard.descargador.R;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class CoverArtLoader {
    private static CoverArtLoader instance;
    private final LruCache<String, Bitmap> cache;
    private final ExecutorService executor = Executors.newFixedThreadPool(4);
    private final Handler handler = new Handler(Looper.getMainLooper());

    private CoverArtLoader() {
        int maxMemory = (int) (Runtime.getRuntime().maxMemory() / 1024);
        cache = new LruCache<>(maxMemory / 8);
    }

    public static synchronized CoverArtLoader getInstance() {
        if (instance == null) instance = new CoverArtLoader();
        return instance;
    }

    public void loadSongCover(String songPath, ImageView imageView) {
        if (songPath == null || imageView == null) return;

        // If online YouTube thumbnail url, delegate to ImageLoader
        if (songPath.startsWith("http://") || songPath.startsWith("https://")) {
            ImageLoader.getInstance().load(songPath, imageView);
            return;
        }

        imageView.setTag(songPath);

        Bitmap cached = cache.get(songPath);
        if (cached != null) {
            imageView.setImageBitmap(cached);
            return;
        }

        executor.execute(() -> {
            Bitmap bmp = null;
            try {
                MediaMetadataRetriever mmr = new MediaMetadataRetriever();
                mmr.setDataSource(songPath);
                byte[] data = mmr.getEmbeddedPicture();
                mmr.release();
                if (data != null && data.length > 0) {
                    bmp = BitmapFactory.decodeByteArray(data, 0, data.length);
                }
            } catch (Exception ignored) {}

            final Bitmap result = bmp;
            handler.post(() -> {
                if (songPath.equals(imageView.getTag())) {
                    if (result != null) {
                        cache.put(songPath, result);
                        imageView.setImageBitmap(result);
                    } else {
                        imageView.setImageResource(R.drawable.ic_music_note);
                    }
                }
            });
        });
    }
}
