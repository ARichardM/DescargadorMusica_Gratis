package cl.arichard.descargador.service;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import androidx.core.app.NotificationCompat;
import cl.arichard.descargador.NowPlayingActivity;
import cl.arichard.descargador.R;
import cl.arichard.descargador.model.Song;
import cl.arichard.descargador.player.PlayerManager;

public class MusicService extends Service {
    public static final String CHANNEL_ID = "musicbox_channel";
    public static final int NOTIFICATION_ID = 2024;

    public static final String ACTION_TOGGLE = "cl.arichard.descargador.TOGGLE";
    public static final String ACTION_NEXT = "cl.arichard.descargador.NEXT";
    public static final String ACTION_PREV = "cl.arichard.descargador.PREV";
    public static final String ACTION_STOP = "cl.arichard.descargador.STOP";
    public static final String ACTION_UPDATE = "cl.arichard.descargador.UPDATE";

    public static final String EXTRA_TITLE = "extra_title";
    public static final String EXTRA_ARTIST = "extra_artist";
    public static final String EXTRA_IS_PLAYING = "extra_is_playing";

    @Override public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null) {
            String action = intent.getAction();
            PlayerManager pm = PlayerManager.getInstance();

            if (ACTION_TOGGLE.equals(action)) {
                pm.togglePlayPause();
            } else if (ACTION_NEXT.equals(action)) {
                pm.playNext();
            } else if (ACTION_PREV.equals(action)) {
                pm.playPrevious();
            } else if (ACTION_STOP.equals(action)) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    stopForeground(STOP_FOREGROUND_REMOVE);
                } else {
                    stopForeground(true);
                }
                stopSelf();
                return START_NOT_STICKY;
            }

            // Always call startForeground immediately to satisfy Android's 5s requirement
            String title = intent.getStringExtra(EXTRA_TITLE);
            String artist = intent.getStringExtra(EXTRA_ARTIST);
            boolean isPlaying = intent.getBooleanExtra(EXTRA_IS_PLAYING, true);

            if (title == null && pm.getCurrentSong() != null) {
                title = pm.getCurrentSong().getTitle();
                artist = pm.getCurrentSong().getArtist();
                isPlaying = pm.isPlaying();
            }

            if (title != null) {
                Notification notification = buildNotification(title, artist != null ? artist : "MusicBox", isPlaying);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
                } else {
                    startForeground(NOTIFICATION_ID, notification);
                }
            }
        }
        return START_NOT_STICKY;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Reproductor de Música",
                NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Controles de música en segundo plano");
            channel.setShowBadge(false);
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) nm.createNotificationChannel(channel);
        }
    }

    private Notification buildNotification(String title, String artist, boolean isPlaying) {
        PendingIntent openApp = PendingIntent.getActivity(
            this, 0,
            new Intent(this, NowPlayingActivity.class),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        PendingIntent pPrev = PendingIntent.getService(
            this, 1,
            new Intent(this, MusicService.class).setAction(ACTION_PREV),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        PendingIntent pToggle = PendingIntent.getService(
            this, 2,
            new Intent(this, MusicService.class).setAction(ACTION_TOGGLE),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        PendingIntent pNext = PendingIntent.getService(
            this, 3,
            new Intent(this, MusicService.class).setAction(ACTION_NEXT),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        int playIcon = isPlaying ? R.drawable.ic_pause : R.drawable.ic_play_arrow;

        return new NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_music_note)
            .setContentTitle(title)
            .setContentText(artist)
            .setContentIntent(openApp)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .addAction(R.drawable.ic_skip_previous, "Anterior", pPrev)
            .addAction(playIcon, isPlaying ? "Pausar" : "Reproducir", pToggle)
            .addAction(R.drawable.ic_skip_next, "Siguiente", pNext)
            .setOngoing(isPlaying)
            .build();
    }

    public static void updateNotification(Context context, Song song, boolean isPlaying) {
        if (song == null || context == null) return;
        try {
            Intent serviceIntent = new Intent(context, MusicService.class);
            serviceIntent.setAction(ACTION_UPDATE);
            serviceIntent.putExtra(EXTRA_TITLE, song.getTitle());
            serviceIntent.putExtra(EXTRA_ARTIST, song.getArtist());
            serviceIntent.putExtra(EXTRA_IS_PLAYING, isPlaying);

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent);
            } else {
                context.startService(serviceIntent);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override public IBinder onBind(Intent intent) { return null; }
}
