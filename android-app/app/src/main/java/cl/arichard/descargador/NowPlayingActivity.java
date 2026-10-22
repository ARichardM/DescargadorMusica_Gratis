package cl.arichard.descargador;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.view.MotionEvent;
import android.view.VelocityTracker;
import android.view.View;
import android.view.animation.OvershootInterpolator;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import cl.arichard.descargador.data.PlaylistManager;
import cl.arichard.descargador.model.Song;
import cl.arichard.descargador.player.PlayerManager;
import cl.arichard.descargador.util.CoverArtLoader;
import cl.arichard.descargador.util.StorageUtil;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;
import java.io.File;

public class NowPlayingActivity extends AppCompatActivity implements PlayerManager.PlaybackListener {

    public static final String EXTRA_VIDEO_ID = "extra_video_id";
    public static final String EXTRA_URL = "extra_url";
    public static final String EXTRA_TITLE = "extra_title";
    public static final String EXTRA_CHANNEL = "extra_channel";
    public static final String EXTRA_THUMBNAIL = "extra_thumbnail";

    private View nowPlayingRoot;
    private ImageView btnBack, btnAction;
    private TextView tabSelectorMp3, tabSelectorMp4;
    private FrameLayout containerCoverArt, containerVideoPlayer, videoHostLayout;
    private ImageView imgNowPlayingCover;
    private TextView txtTitle, txtArtist;
    private SeekBar seekBar;
    private TextView txtCurrentTime, txtTotalTime;

    private ImageView btnShuffle, btnPrevious, btnPlayPauseIcon, btnNext, btnRepeat;
    private FrameLayout btnPlayPauseCircle;

    // Download Banner
    private LinearLayout playerDownloadCard;
    private TextView txtPlayerDownloadStatus, txtPlayerDownloadEta;
    private ProgressBar playerDownloadProgress;

    private boolean isMp3Mode = true;
    private boolean isUserSeeking = false;
    private boolean isDownloading = false;
    private float initialTouchY = 0;
    private boolean isDraggingDown = false;
    private VelocityTracker velocityTracker;

    private String onlineVideoId;
    private String onlineUrl;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_now_playing);

        initViews();
        setupClickListeners();
        setupSwipeDownToDismiss();

        handleIncomingIntent(getIntent());
    }

    private void initViews() {
        nowPlayingRoot = findViewById(R.id.nowPlayingRoot);
        btnBack = findViewById(R.id.btnBackNowPlaying);
        btnAction = findViewById(R.id.btnNowPlayingAction);

        tabSelectorMp3 = findViewById(R.id.tabSelectorMp3);
        tabSelectorMp4 = findViewById(R.id.tabSelectorMp4);

        containerCoverArt = findViewById(R.id.containerCoverArt);
        containerVideoPlayer = findViewById(R.id.containerVideoPlayer);
        videoHostLayout = findViewById(R.id.videoHostLayout);
        imgNowPlayingCover = findViewById(R.id.imgNowPlayingCover);

        txtTitle = findViewById(R.id.txtNowPlayingTitle);
        txtArtist = findViewById(R.id.txtNowPlayingArtist);
        txtCurrentTime = findViewById(R.id.txtCurrentTime);
        txtTotalTime = findViewById(R.id.txtTotalTime);
        seekBar = findViewById(R.id.seekBar);

        btnShuffle = findViewById(R.id.btnShuffle);
        btnPrevious = findViewById(R.id.btnPrevious);
        btnPlayPauseCircle = findViewById(R.id.btnPlayPauseCircle);
        btnPlayPauseIcon = findViewById(R.id.btnPlayPauseIcon);
        btnNext = findViewById(R.id.btnNext);
        btnRepeat = findViewById(R.id.btnRepeat);

        playerDownloadCard = findViewById(R.id.playerDownloadCard);
        txtPlayerDownloadStatus = findViewById(R.id.txtPlayerDownloadStatus);
        txtPlayerDownloadEta = findViewById(R.id.txtPlayerDownloadEta);
        playerDownloadProgress = findViewById(R.id.playerDownloadProgress);

        txtTitle.setSelected(true);
    }

    private void handleIncomingIntent(Intent intent) {
        if (intent == null) return;
        String vid = intent.getStringExtra(EXTRA_VIDEO_ID);
        String url = intent.getStringExtra(EXTRA_URL);
        if (vid != null && !vid.isEmpty()) {
            onlineVideoId = vid;
            onlineUrl = url;
        }
    }

    private void setupClickListeners() {
        btnBack.setOnClickListener(v -> closeWithSlideDown());

        tabSelectorMp3.setOnClickListener(v -> setMediaMode(true));
        tabSelectorMp4.setOnClickListener(v -> setMediaMode(false));

        btnPlayPauseCircle.setOnClickListener(v -> PlayerManager.getInstance().togglePlayPause());
        btnNext.setOnClickListener(v -> PlayerManager.getInstance().playNext());
        btnPrevious.setOnClickListener(v -> PlayerManager.getInstance().playPrevious());

        btnShuffle.setOnClickListener(v -> {
            boolean active = PlayerManager.getInstance().toggleShuffle();
            updateShuffleButton(active);
        });

        btnRepeat.setOnClickListener(v -> {
            int mode = PlayerManager.getInstance().toggleRepeat();
            updateRepeatButton(mode);
        });

        btnAction.setOnClickListener(v -> {
            if (PlayerManager.getInstance().isOnlineTrack()) {
                startTrackDownload();
            } else {
                Song current = PlayerManager.getInstance().getCurrentSong();
                if (current != null) {
                    boolean fav = PlaylistManager.getInstance(this).toggleFavorite(current.getPath());
                    btnAction.setImageResource(fav ? R.drawable.ic_favorite_filled : R.drawable.ic_favorite);
                }
            }
        });

        seekBar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar sb, int progress, boolean fromUser) {
                if (fromUser) {
                    txtCurrentTime.setText(formatTime(progress));
                }
            }
            @Override public void onStartTrackingTouch(SeekBar sb) { isUserSeeking = true; }
            @Override public void onStopTrackingTouch(SeekBar sb) {
                isUserSeeking = false;
                PlayerManager.getInstance().seekTo(sb.getProgress());
            }
        });
    }

    private void setMediaMode(boolean mp3) {
        isMp3Mode = mp3;
        if (mp3) PlayerManager.getInstance().detachOnlineWebView();
        else PlayerManager.getInstance().attachOnlineWebView(videoHostLayout);
        int activeText = ContextCompat.getColor(this, R.color.chip_active_text);
        int inactiveText = ContextCompat.getColor(this, R.color.text_secondary);

        if (isMp3Mode) {
            tabSelectorMp3.setBackgroundResource(R.drawable.bg_chip_active);
            tabSelectorMp3.setTextColor(activeText);
            tabSelectorMp4.setBackground(null);
            tabSelectorMp4.setTextColor(inactiveText);

            containerCoverArt.setVisibility(View.VISIBLE);
            containerVideoPlayer.setVisibility(View.INVISIBLE); // Keep measured and rendering
        } else {
            tabSelectorMp4.setBackgroundResource(R.drawable.bg_chip_active);
            tabSelectorMp4.setTextColor(activeText);
            tabSelectorMp3.setBackground(null);
            tabSelectorMp3.setTextColor(inactiveText);

            containerCoverArt.setVisibility(View.GONE);
            containerVideoPlayer.setVisibility(View.VISIBLE);
        }
    }

    private void startTrackDownload() {
        if (isDownloading) {
            Toast.makeText(this, "Descarga en curso", Toast.LENGTH_SHORT).show();
            return;
        }

        String downloadUrl = onlineUrl;
        if ((downloadUrl == null || downloadUrl.isEmpty()) && onlineVideoId != null) {
            downloadUrl = "https://www.youtube.com/watch?v=" + onlineVideoId;
        }
        if (downloadUrl == null) {
            downloadUrl = PlayerManager.getInstance().getCurrentOnlineUrl();
        }
        if (downloadUrl == null) {
            Toast.makeText(this, "No se puede descargar esta pista", Toast.LENGTH_SHORT).show();
            return;
        }

        File dir = StorageUtil.getDownloadDir(this);
        YoutubeDLRequest request = new YoutubeDLRequest(downloadUrl);
        request.addOption("--no-playlist");
        request.addOption("--no-update");
        request.addOption("--extractor-args", "youtube:player_client=android,web");
        request.addOption("--no-mtime");
        request.addOption("--restrict-filenames");
        request.addOption("-o", new File(dir, "%(title).160s.%(ext)s").getAbsolutePath());

        if (isMp3Mode) {
            request.addOption("-x");
            request.addOption("--audio-format", "mp3");
            request.addOption("--audio-quality", "192K");
            request.addOption("--embed-thumbnail");
            request.addOption("--add-metadata");
        } else {
            request.addOption("-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best");
            request.addOption("--merge-output-format", "mp4");
        }

        isDownloading = true;
        playerDownloadCard.setVisibility(View.VISIBLE);
        playerDownloadProgress.setProgress(0);
        txtPlayerDownloadStatus.setText("Iniciando descarga (" + (isMp3Mode ? "MP3" : "MP4") + ")...");
        txtPlayerDownloadEta.setText("Conectando...");

        DescargadorApp.IO.execute(() -> {
            try {
                YoutubeDL.getInstance().execute(request, "now-playing-dl", (percent, eta, line) -> {
                    runOnUiThread(() -> {
                        int p = Math.round(percent);
                        playerDownloadProgress.setProgress(p);
                        txtPlayerDownloadStatus.setText("Descargando " + p + "% (" + (isMp3Mode ? "MP3" : "MP4") + ")");
                        txtPlayerDownloadEta.setText("Faltan aprox. " + eta + " s");
                    });
                    return kotlin.Unit.INSTANCE;
                });

                runOnUiThread(() -> {
                    playerDownloadProgress.setProgress(100);
                    txtPlayerDownloadStatus.setText("Descarga completada (" + (isMp3Mode ? "MP3" : "MP4") + ")");
                    txtPlayerDownloadEta.setText("Guardado en descargas");
                    isDownloading = false;
                    playerDownloadCard.postDelayed(() -> playerDownloadCard.setVisibility(View.GONE), 3500);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    txtPlayerDownloadStatus.setText("Error en la descarga");
                    txtPlayerDownloadEta.setText(e.getMessage() != null ? e.getMessage() : "Error");
                    isDownloading = false;
                    playerDownloadCard.postDelayed(() -> playerDownloadCard.setVisibility(View.GONE), 4000);
                });
            }
        });
    }

    private void setupSwipeDownToDismiss() {
        nowPlayingRoot.setOnTouchListener((v, event) -> {
            if (velocityTracker == null) {
                velocityTracker = VelocityTracker.obtain();
            }
            velocityTracker.addMovement(event);

            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    initialTouchY = event.getRawY();
                    isDraggingDown = false;
                    return true;

                case MotionEvent.ACTION_MOVE:
                    float dy = event.getRawY() - initialTouchY;
                    if (dy > 12 && !isDraggingDown) {
                        isDraggingDown = true;
                    }
                    if (isDraggingDown) {
                        if (dy > 0) {
                            nowPlayingRoot.setTranslationY(dy);
                            float progress = Math.min(1.0f, dy / (float) getResources().getDisplayMetrics().heightPixels);
                            nowPlayingRoot.setAlpha(1.0f - (progress * 0.45f));
                        } else {
                            float rubberBand = (float) (-Math.pow(-dy, 0.72) * 1.5);
                            nowPlayingRoot.setTranslationY(rubberBand);
                            nowPlayingRoot.setAlpha(1.0f);
                        }
                        return true;
                    }
                    break;

                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    if (isDraggingDown) {
                        float finalDy = event.getRawY() - initialTouchY;
                        velocityTracker.computeCurrentVelocity(1000);
                        float yVelocity = velocityTracker.getYVelocity();

                        int screenHeight = getResources().getDisplayMetrics().heightPixels;
                        boolean shouldDismiss = finalDy > (screenHeight * 0.22f) || yVelocity > 1400;

                        if (shouldDismiss) {
                            closeWithSlideDown();
                        } else {
                            nowPlayingRoot.animate()
                                    .translationY(0)
                                    .alpha(1.0f)
                                    .setDuration(280)
                                    .setInterpolator(new OvershootInterpolator(0.9f))
                                    .start();
                        }
                        isDraggingDown = false;
                        if (velocityTracker != null) {
                            velocityTracker.recycle();
                            velocityTracker = null;
                        }
                        return true;
                    }
                    break;
            }
            return false;
        });
    }

    private void closeWithSlideDown() {
        int screenHeight = getResources().getDisplayMetrics().heightPixels;
        nowPlayingRoot.animate()
                .translationY(screenHeight)
                .alpha(0.0f)
                .setDuration(220)
                .withEndAction(this::finish)
                .start();
    }

    @Override
    public void onBackPressed() {
        closeWithSlideDown();
    }

    @Override
    protected void onResume() {
        super.onResume();
        PlayerManager.getInstance().addListener(this);


        Song current = PlayerManager.getInstance().getCurrentSong();
        if (current != null) {
            updateSongInfo(current);
            updatePlaybackState(PlayerManager.getInstance().isPlaying());
            int pos = PlayerManager.getInstance().getCurrentPosition();
            int dur = PlayerManager.getInstance().getDuration();
            updateProgress(pos, dur);
        }
        updateShuffleButton(PlayerManager.getInstance().isShuffle());
        updateRepeatButton(PlayerManager.getInstance().getRepeatMode());
        setMediaMode(isMp3Mode);
        onPlaybackLoading(PlayerManager.getInstance().isLoading());
    }

    @Override
    protected void onPause() {
        super.onPause();
        PlayerManager.getInstance().removeListener(this);
        if (PlayerManager.getInstance().isOnlineTrack()) {
            PlayerManager.getInstance().detachOnlineWebView();
        }
    }

    private void updateSongInfo(Song song) {
        if (song == null) return;
        txtTitle.setText(song.getTitle());
        txtArtist.setText(song.getArtist());

        if (PlayerManager.getInstance().isOnlineTrack()) {
            btnAction.setImageResource(R.drawable.ic_download);
        } else {
            boolean fav = PlaylistManager.getInstance(this).isFavorite(song.getPath());
            btnAction.setImageResource(fav ? R.drawable.ic_favorite_filled : R.drawable.ic_favorite);
        }

        if (imgNowPlayingCover != null) {
            CoverArtLoader.getInstance().loadSongCover(song.getPath(), imgNowPlayingCover);
        }
    }

    private void updatePlaybackState(boolean isPlaying) {
        btnPlayPauseIcon.setImageResource(isPlaying ? R.drawable.ic_pause : R.drawable.ic_play_arrow);
    }

    private void updateProgress(int pos, int dur) {
        if (dur > 0) {
            seekBar.setMax(dur);
            seekBar.setProgress(pos);
            txtCurrentTime.setText(formatTime(pos));
            txtTotalTime.setText(formatTime(dur));
        } else {
            seekBar.setProgress(0);
            txtCurrentTime.setText("00:00");
            txtTotalTime.setText("00:00");
        }
    }

    private void updateShuffleButton(boolean active) {
        btnShuffle.setAlpha(active ? 1.0f : 0.45f);
        btnShuffle.setColorFilter(active ? ContextCompat.getColor(this, R.color.chip_active_text) : ContextCompat.getColor(this, R.color.text_primary));
    }

    private void updateRepeatButton(int mode) {
        if (mode == PlayerManager.REPEAT_OFF) {
            btnRepeat.setAlpha(0.45f);
            btnRepeat.setImageResource(R.drawable.ic_repeat);
            btnRepeat.setColorFilter(ContextCompat.getColor(this, R.color.text_primary));
        } else if (mode == PlayerManager.REPEAT_ALL) {
            btnRepeat.setAlpha(1.0f);
            btnRepeat.setImageResource(R.drawable.ic_repeat);
            btnRepeat.setColorFilter(ContextCompat.getColor(this, R.color.chip_active_text));
        } else {
            btnRepeat.setAlpha(1.0f);
            btnRepeat.setImageResource(R.drawable.ic_repeat_one);
            btnRepeat.setColorFilter(ContextCompat.getColor(this, R.color.chip_active_text));
        }
    }

    private String formatTime(int ms) {
        int totalSec = ms / 1000;
        int m = totalSec / 60;
        int s = totalSec % 60;
        return String.format("%02d:%02d", m, s);
    }

    @Override
    public void onTrackChanged(Song song) {
        runOnUiThread(() -> updateSongInfo(song));
    }

    @Override
    public void onPlaybackLoading(boolean loading) {
        if (loading) txtCurrentTime.setText("Cargando…");
    }

    @Override
    public void onPlaybackError(String message) {
        txtCurrentTime.setText("Error");
        txtTotalTime.setText("Reintentar ▶");
    }

    @Override
    public void onPlaybackStateChanged(boolean isPlaying) {
        runOnUiThread(() -> updatePlaybackState(isPlaying));
    }

    @Override
    public void onProgressUpdate(int currentPos, int duration) {
        if (!isUserSeeking) {
            runOnUiThread(() -> updateProgress(currentPos, duration));
        }
    }
}
