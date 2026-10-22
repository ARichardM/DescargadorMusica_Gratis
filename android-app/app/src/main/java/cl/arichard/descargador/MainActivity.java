package cl.arichard.descargador;

import cl.arichard.descargador.util.StorageUtil;

import android.Manifest;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.text.Editable;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.view.View;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.animation.AnimationUtils;
import android.view.animation.OvershootInterpolator;
import cl.arichard.descargador.util.CoverArtLoader;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.app.AppCompatDelegate;
import androidx.appcompat.widget.PopupMenu;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;
import com.yausername.youtubedl_android.YoutubeDLResponse;
import cl.arichard.descargador.adapter.FolderAdapter;
import cl.arichard.descargador.adapter.PlaylistAdapter;
import cl.arichard.descargador.adapter.SearchResultAdapter;
import cl.arichard.descargador.adapter.SongAdapter;
import cl.arichard.descargador.data.SearchHistoryManager;
import androidx.core.widget.NestedScrollView;
import cl.arichard.descargador.data.MusicScanner;
import cl.arichard.descargador.data.PlaylistManager;
import cl.arichard.descargador.model.SearchResult;
import cl.arichard.descargador.model.Song;
import cl.arichard.descargador.player.PlayerManager;
import org.json.JSONObject;
import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.HashSet;
import java.util.Set;
import java.util.ArrayDeque;
import java.util.LinkedHashMap;

public class MainActivity extends AppCompatActivity implements PlayerManager.PlaybackListener {

    private GestureDetector tabGestureDetector;
    private ImageView imgMiniCover;
    private float miniPlayerTouchY = 0;
    private boolean isDraggingMiniPlayer = false;
    private boolean currentTabIsSearch = true;

    private static final Pattern YOUTUBE = Pattern.compile("(?:youtu\\.be/|youtube(?:\\.com)?/.*?[?&]v=|youtube\\.com/(?:shorts|embed)/)([A-Za-z0-9_-]{11})");
    private static final String PREFS_NAME = "musicbox_prefs";
    private static final String KEY_DARK_MODE = "dark_mode";

    // Navigation Island
    private LinearLayout navTabSearch, navTabLibrary;
    private ImageView navIconSearch, navIconLibrary;
    private TextView navLabelSearch, navLabelLibrary;
    private View tabSearch, tabLibrary;

    // Search Tab Views
    private ImageView btnThemeToggle, btnPaste;
    private EditText inputSearch;
    private TextView txtSearchStatus, txtSearchHint;
    // Discovery Views
    private NestedScrollView containerSearchDiscovery;
    private View sectionRecentQueries, sectionRecentPlays, sectionTopLibrary;
    private LinearLayout layoutRecentChips, layoutRecentPlaysCards, layoutTopLibraryList;
    private TextView btnClearSearchHistory;

    private ProgressBar searchLoading;
    private RecyclerView recyclerSearchResults;
    private SearchResultAdapter searchResultAdapter;
    private LinearLayout cardProgress;
    private TextView txtStatus, txtEta;
    private ProgressBar progressBar;
    private boolean isMp3 = true;
    private volatile boolean downloading = false;
    private final ArrayDeque<DownloadJob> downloadQueue = new ArrayDeque<>();
    private final Map<String, List<SearchResult>> searchCache = new LinkedHashMap<String, List<SearchResult>>(8, .75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<String, List<SearchResult>> eldest) { return size() > 8; }
    };

    private static class DownloadJob {
        final String url, title, videoId;
        DownloadJob(String url, String title, String videoId) { this.url = url; this.title = title; this.videoId = videoId; }
    }

    // Library Tab Views
    private ImageView btnBackLibrary, btnShuffleAll;
    private TextView txtLibraryTitle, txtSongCount;
    private EditText inputSearchLibrary;
    // Library Filter Views
    private ImageView btnClearLibraryFilter;
    private View scrollLibraryFilters;
    private TextView chipFilterAll, chipFilterFavorites, chipFilterRecent, chipFilterAZ;
    private int currentSongFilter = 0; // 0=All, 1=Fav, 2=Recent, 3=AZ

    private TextView chipSongs, chipFolders, chipPlaylists;
    private RecyclerView recyclerLibrary;
    private FrameLayout fabNewPlaylist, btnNewPlaylist;
    private SongAdapter songAdapter;
    private FolderAdapter folderAdapter;
    private PlaylistAdapter playlistAdapter;
    private final List<Song> allSongs = new ArrayList<>();
    private int currentLibraryMode = 0; // 0=Songs, 1=Folders, 2=Playlists
    private boolean isViewingSubList = false;

    // Mini Player
    private LinearLayout miniPlayerLayout;
    private TextView txtMiniTitle, txtMiniArtist;
    private ImageView btnMiniPlayPause, btnMiniNext;
    private ProgressBar miniProgress;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // Apply saved theme preference before inflating view
        // Theme is already initialized in DescargadorApp.onCreate()

        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        PlayerManager.getInstance().setMainActivityHost(findViewById(R.id.globalWebVideoContainer));

        initViews();
        setupNavigation();
        setupSearchTab();
        setupLibraryTab();
        setupMiniPlayer();
        checkPermissionsAndScan();
        handleIntent(getIntent());
    }

    private void initViews() {
        // Nav Island
        navTabSearch = findViewById(R.id.navTabSearch);
        navTabLibrary = findViewById(R.id.navTabLibrary);
        navIconSearch = findViewById(R.id.navIconSearch);
        navIconLibrary = findViewById(R.id.navIconLibrary);
        navLabelSearch = findViewById(R.id.navLabelSearch);
        navLabelLibrary = findViewById(R.id.navLabelLibrary);
        tabSearch = findViewById(R.id.tabSearch);
        tabLibrary = findViewById(R.id.tabLibrary);

        // Search Tab
        btnThemeToggle = findViewById(R.id.btnThemeToggle);
        inputSearch = findViewById(R.id.inputSearch);
        containerSearchDiscovery = findViewById(R.id.containerSearchDiscovery);
        sectionRecentQueries = findViewById(R.id.sectionRecentQueries);
        sectionRecentPlays = findViewById(R.id.sectionRecentPlays);
        sectionTopLibrary = findViewById(R.id.sectionTopLibrary);
        layoutRecentChips = findViewById(R.id.layoutRecentChips);
        layoutRecentPlaysCards = findViewById(R.id.layoutRecentPlaysCards);
        layoutTopLibraryList = findViewById(R.id.layoutTopLibraryList);
        btnClearSearchHistory = findViewById(R.id.btnClearSearchHistory);
        if (btnClearSearchHistory != null) {
            btnClearSearchHistory.setOnClickListener(v -> {
                SearchHistoryManager.getInstance(this).clearRecentQueries();
                populateRecentQueries();
            });
        }

        btnPaste = findViewById(R.id.btnPaste);

        txtSearchStatus = findViewById(R.id.txtSearchStatus);
        txtSearchHint = findViewById(R.id.txtSearchHint);
        searchLoading = findViewById(R.id.searchLoading);
        recyclerSearchResults = findViewById(R.id.recyclerSearchResults);
        cardProgress = findViewById(R.id.cardProgress);
        txtStatus = findViewById(R.id.txtStatus);
        txtEta = findViewById(R.id.txtEta);
        progressBar = findViewById(R.id.progressBar);

        // Library Tab
        btnBackLibrary = findViewById(R.id.btnBackLibrary);
        txtLibraryTitle = findViewById(R.id.txtLibraryTitle);
        btnShuffleAll = findViewById(R.id.btnShuffleAll);
        inputSearchLibrary = findViewById(R.id.inputSearchLibrary);
        chipSongs = findViewById(R.id.chipSongs);
        chipFolders = findViewById(R.id.chipFolders);
        chipPlaylists = findViewById(R.id.chipPlaylists);
        txtSongCount = findViewById(R.id.txtSongCount);
        recyclerLibrary = findViewById(R.id.recyclerLibrary);
        fabNewPlaylist = findViewById(R.id.fabNewPlaylist);
        btnNewPlaylist = findViewById(R.id.btnNewPlaylist);
        btnClearLibraryFilter = findViewById(R.id.btnClearLibraryFilter);
        scrollLibraryFilters = findViewById(R.id.scrollLibraryFilters);
        chipFilterAll = findViewById(R.id.chipFilterAll);
        chipFilterFavorites = findViewById(R.id.chipFilterFavorites);
        chipFilterRecent = findViewById(R.id.chipFilterRecent);
        chipFilterAZ = findViewById(R.id.chipFilterAZ);

        if (btnClearLibraryFilter != null) {
            btnClearLibraryFilter.setOnClickListener(v -> {
                inputSearchLibrary.setText("");
                applyLibraryFilter("");
            });
        }

        if (chipFilterAll != null) chipFilterAll.setOnClickListener(v -> setSongFilter(0));
        if (chipFilterFavorites != null) chipFilterFavorites.setOnClickListener(v -> setSongFilter(1));
        if (chipFilterRecent != null) chipFilterRecent.setOnClickListener(v -> setSongFilter(2));
        if (chipFilterAZ != null) chipFilterAZ.setOnClickListener(v -> setSongFilter(3));


        // Mini Player
        miniPlayerLayout = findViewById(R.id.miniPlayerLayout);
        txtMiniTitle = findViewById(R.id.txtMiniTitle);
        txtMiniArtist = findViewById(R.id.txtMiniArtist);
        btnMiniPlayPause = findViewById(R.id.btnMiniPlayPause);
        btnMiniNext = findViewById(R.id.btnMiniNext);
        miniProgress = findViewById(R.id.miniProgress);
        imgMiniCover = findViewById(R.id.imgMiniCover);
    }

    private void setupNavigation() {
        navTabSearch.setOnClickListener(v -> switchTab(true));
        navTabLibrary.setOnClickListener(v -> switchTab(false));

        // Long press on tabs for quick tactile feedback
        navTabSearch.setOnLongClickListener(v -> { switchTab(true); return true; });
        navTabLibrary.setOnLongClickListener(v -> { switchTab(false); return true; });

        // Horizontal Swipe detector to swipe between Buscar and Mi Música anywhere on the screen
        tabGestureDetector = new GestureDetector(this, new GestureDetector.SimpleOnGestureListener() {
            private static final int SWIPE_THRESHOLD = 90;
            private static final int SWIPE_VELOCITY = 100;

            @Override
            public boolean onFling(MotionEvent e1, MotionEvent e2, float velocityX, float velocityY) {
                if (e1 == null || e2 == null) return false;
                float diffX = e2.getX() - e1.getX();
                float diffY = e2.getY() - e1.getY();
                if (Math.abs(diffX) > Math.abs(diffY)) {
                    if (Math.abs(diffX) > SWIPE_THRESHOLD && Math.abs(velocityX) > SWIPE_VELOCITY) {
                        if (diffX < 0) {
                            switchTab(false); // Swipe Left -> Mi Música
                        } else {
                            switchTab(true);  // Swipe Right -> Buscar
                        }
                        return true;
                    }
                }
                return false;
            }
        });

        // Theme Toggle
        btnThemeToggle.setOnClickListener(v -> {
            SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
            boolean currentlyDark = prefs.getBoolean(KEY_DARK_MODE, true);
            boolean newDark = !currentlyDark;
            prefs.edit().putBoolean(KEY_DARK_MODE, newDark).apply();
            AppCompatDelegate.setDefaultNightMode(newDark ? AppCompatDelegate.MODE_NIGHT_YES : AppCompatDelegate.MODE_NIGHT_NO);
        });
    }

    @Override
    public boolean dispatchTouchEvent(MotionEvent ev) {
        if (tabGestureDetector != null) {
            tabGestureDetector.onTouchEvent(ev);
        }
        return super.dispatchTouchEvent(ev);
    }

    private void switchTab(boolean isSearch) {
        if (currentTabIsSearch == isSearch) return;
        currentTabIsSearch = isSearch;

        int primaryText = ContextCompat.getColor(this, R.color.text_primary);
        int mutedText = ContextCompat.getColor(this, R.color.text_secondary);

        if (isSearch) {
            tabLibrary.startAnimation(AnimationUtils.loadAnimation(this, R.anim.slide_out_right));
            tabLibrary.setVisibility(View.GONE);

            tabSearch.setVisibility(View.VISIBLE);
            tabSearch.startAnimation(AnimationUtils.loadAnimation(this, R.anim.slide_in_left));

            navTabSearch.setBackgroundResource(R.drawable.bg_nav_tab_indicator);
            navIconSearch.setColorFilter(primaryText);
            navLabelSearch.setTextColor(primaryText);

            navTabLibrary.setBackground(null);
            navIconLibrary.setColorFilter(mutedText);
            navLabelLibrary.setTextColor(mutedText);
        } else {
            tabSearch.startAnimation(AnimationUtils.loadAnimation(this, R.anim.slide_out_left));
            tabSearch.setVisibility(View.GONE);

            tabLibrary.setVisibility(View.VISIBLE);
            tabLibrary.startAnimation(AnimationUtils.loadAnimation(this, R.anim.slide_in_right));

            navTabLibrary.setBackgroundResource(R.drawable.bg_nav_tab_indicator);
            navIconLibrary.setColorFilter(primaryText);
            navLabelLibrary.setTextColor(primaryText);

            navTabSearch.setBackground(null);
            navIconSearch.setColorFilter(mutedText);
            navLabelSearch.setTextColor(mutedText);

            refreshMusicLibrary();
        }
    }

    private void setupSearchTab() {


        btnPaste.setOnClickListener(v -> {
            ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (clipboard != null && clipboard.hasPrimaryClip()) {
                ClipData.Item item = clipboard.getPrimaryClip().getItemAt(0);
                CharSequence text = item.getText();
                if (text != null && !TextUtils.isEmpty(text)) {
                    inputSearch.setText(text.toString().trim());
                    inputSearch.setSelection(inputSearch.getText().length());
                    triggerSearchOrDownload(text.toString().trim());
                }
            }
        });

        searchResultAdapter = new SearchResultAdapter(this, new SearchResultAdapter.OnResultClickListener() {
            @Override
            public void onAddClick(SearchResult result, View anchor) {
                showAddOnlineToPlaylistDialog(result);
            }

            @Override
            public void onPlayClick(SearchResult result) {
                playOnlineResult(result, false);
            }

            @Override
            public void onFavoriteChanged(SearchResult result, boolean favorite) {
                if (favorite && PlaylistManager.getInstance(MainActivity.this).isAutoDownloadEnabled("Favoritos")) {
                    startDownload(result.getUrl(), result.getTitle(), result.getId());
                }
            }

            @Override
            public void onItemClick(SearchResult result) {
                playOnlineResult(result, true);
            }
        });

        refreshDownloadedBadges();

        recyclerSearchResults.setLayoutManager(new LinearLayoutManager(this));
        recyclerSearchResults.setAdapter(searchResultAdapter);

        inputSearch.setOnEditorActionListener((v, actionId, event) -> {
            boolean isEnter = (event != null && event.getKeyCode() == android.view.KeyEvent.KEYCODE_ENTER && event.getAction() == android.view.KeyEvent.ACTION_DOWN);
            if (actionId == EditorInfo.IME_ACTION_SEARCH || actionId == EditorInfo.IME_ACTION_DONE || isEnter) {
                hideKeyboard();
                String query = inputSearch.getText().toString().trim();
                if (!query.isEmpty()) triggerSearchOrDownload(query);
                return true;
            }
            return false;
        });
    }

    private void playOnlineResult(SearchResult result, boolean openPlayer) {
                SearchHistoryManager.getInstance(MainActivity.this).recordPlayedSong(
                    new Song(System.currentTimeMillis(), result.getTitle(), result.getChannel(), "YouTube", 0, result.getThumbnailUrl(), result.getId(), System.currentTimeMillis())
                );
                PlayerManager.getInstance().playOnline(
                    result.getId(),
                    result.getTitle(),
                    result.getChannel(),
                    result.getThumbnailUrl(),
                    result.getUrl()
                );
        if (openPlayer) {
                Intent intent = new Intent(MainActivity.this, NowPlayingActivity.class);
                intent.putExtra(NowPlayingActivity.EXTRA_VIDEO_ID, result.getId());
                intent.putExtra(NowPlayingActivity.EXTRA_URL, result.getUrl());
                intent.putExtra(NowPlayingActivity.EXTRA_TITLE, result.getTitle());
                intent.putExtra(NowPlayingActivity.EXTRA_CHANNEL, result.getChannel());
                intent.putExtra(NowPlayingActivity.EXTRA_THUMBNAIL, result.getThumbnailUrl());
                startActivity(intent);
        }
    }




    private void refreshDiscoveryContent() {
        populateRecentQueries();
        populateRecentPlays();
        populateTopLibrary();
    }

    private void populateRecentQueries() {
        if (layoutRecentChips == null || sectionRecentQueries == null) return;
        List<String> queries = SearchHistoryManager.getInstance(this).getRecentQueries();
        if (queries.isEmpty()) {
            sectionRecentQueries.setVisibility(View.GONE);
            return;
        }
        sectionRecentQueries.setVisibility(View.VISIBLE);
        layoutRecentChips.removeAllViews();

        int chipBg = ContextCompat.getColor(this, R.color.bg_card);
        int textColor = ContextCompat.getColor(this, R.color.text_primary);

        for (String q : queries) {
            TextView chip = new TextView(this);
            chip.setText(q);
            chip.setTextColor(textColor);
            chip.setTextSize(13f);
            chip.setBackgroundResource(R.drawable.bg_chip_inactive);
            chip.setPadding(32, 16, 32, 16);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );
            lp.setMargins(0, 0, 16, 0);
            chip.setLayoutParams(lp);
            chip.setOnClickListener(v -> {
                inputSearch.setText(q);
                inputSearch.setSelection(q.length());
                triggerSearchOrDownload(q);
            });
            layoutRecentChips.addView(chip);
        }
    }

    private void populateRecentPlays() {
        if (layoutRecentPlaysCards == null || sectionRecentPlays == null) return;
        List<Song> recents = SearchHistoryManager.getInstance(this).getRecentPlayedSongs();
        if (recents.isEmpty()) {
            sectionRecentPlays.setVisibility(View.GONE);
            return;
        }
        sectionRecentPlays.setVisibility(View.VISIBLE);
        layoutRecentPlaysCards.removeAllViews();

        int textColor = ContextCompat.getColor(this, R.color.text_primary);
        int subColor = ContextCompat.getColor(this, R.color.text_secondary);

        for (Song s : recents) {
            LinearLayout card = new LinearLayout(this);
            card.setOrientation(LinearLayout.VERTICAL);
            card.setGravity(android.view.Gravity.CENTER_HORIZONTAL);
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(260, LinearLayout.LayoutParams.WRAP_CONTENT);
            lp.setMargins(0, 0, 24, 0);
            card.setLayoutParams(lp);

            androidx.cardview.widget.CardView cv = new androidx.cardview.widget.CardView(this);
            cv.setRadius(24f);
            cv.setCardElevation(4f);
            LinearLayout.LayoutParams cvLp = new LinearLayout.LayoutParams(240, 240);
            cv.setLayoutParams(cvLp);

            ImageView iv = new ImageView(this);
            iv.setScaleType(ImageView.ScaleType.CENTER_CROP);
            cv.addView(iv, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
            CoverArtLoader.getInstance().loadSongCover(s.getPath(), iv);

            TextView txtT = new TextView(this);
            txtT.setText(s.getTitle());
            txtT.setTextColor(textColor);
            txtT.setTextSize(13f);
            txtT.setTypeface(null, android.graphics.Typeface.BOLD);
            txtT.setSingleLine(true);
            txtT.setEllipsize(android.text.TextUtils.TruncateAt.END);
            txtT.setPadding(4, 10, 4, 2);

            TextView txtA = new TextView(this);
            txtA.setText(s.getArtist());
            txtA.setTextColor(subColor);
            txtA.setTextSize(11f);
            txtA.setSingleLine(true);
            txtA.setEllipsize(android.text.TextUtils.TruncateAt.END);
            txtA.setPadding(4, 0, 4, 0);

            card.addView(cv);
            card.addView(txtT);
            card.addView(txtA);

            card.setOnClickListener(v -> {
                if ("YouTube".equals(s.getFolder())) {
                    String vid = s.getPath();
                    String thumb = "https://i.ytimg.com/vi/" + vid + "/hqdefault.jpg";
                    PlayerManager.getInstance().playOnline(
                        vid, s.getTitle(), s.getArtist(), thumb, "https://www.youtube.com/watch?v=" + vid
                    );
                    Intent intent = new Intent(MainActivity.this, NowPlayingActivity.class);
                    intent.putExtra(NowPlayingActivity.EXTRA_VIDEO_ID, vid);
                    intent.putExtra(NowPlayingActivity.EXTRA_URL, "https://www.youtube.com/watch?v=" + vid);
                    intent.putExtra(NowPlayingActivity.EXTRA_TITLE, s.getTitle());
                    intent.putExtra(NowPlayingActivity.EXTRA_CHANNEL, s.getArtist());
                    intent.putExtra(NowPlayingActivity.EXTRA_THUMBNAIL, thumb);
                    startActivity(intent);
                } else {
                    PlayerManager.getInstance().playSong(s, Collections.singletonList(s));
                    startActivity(new Intent(MainActivity.this, NowPlayingActivity.class));
                }
            });

            layoutRecentPlaysCards.addView(card);
        }
    }

    private void populateTopLibrary() {
        if (layoutTopLibraryList == null || sectionTopLibrary == null) return;
        List<Song> topSongs = SearchHistoryManager.getInstance(this).getTopPlayed(allSongs, 5);
        if (topSongs.isEmpty()) {
            sectionTopLibrary.setVisibility(View.GONE);
            return;
        }
        sectionTopLibrary.setVisibility(View.VISIBLE);
        layoutTopLibraryList.removeAllViews();

        for (Song s : topSongs) {
            View itemView = getLayoutInflater().inflate(R.layout.item_song, layoutTopLibraryList, false);
            TextView title = itemView.findViewById(R.id.txtSongTitle);
            TextView sub = itemView.findViewById(R.id.txtSongSubtitle);
            ImageView cover = itemView.findViewById(R.id.imgSongCover);
            View btnFav = itemView.findViewById(R.id.btnFavorite);
            View btnMenu = itemView.findViewById(R.id.btnSongMenu);

            title.setText(s.getTitle());
            sub.setText(s.getArtist() + " • " + s.getFormattedDuration());
            CoverArtLoader.getInstance().loadSongCover(s.getPath(), cover);

            if (btnFav != null) btnFav.setVisibility(View.GONE);
            if (btnMenu != null) btnMenu.setVisibility(View.GONE);

            itemView.setOnClickListener(v -> {
                PlayerManager.getInstance().playSong(s, allSongs);
                SearchHistoryManager.getInstance(this).recordPlayedSong(s);
                startActivity(new Intent(MainActivity.this, NowPlayingActivity.class));
            });

            layoutTopLibraryList.addView(itemView);
        }
    }

    private void triggerSearchOrDownload(String query) {
        SearchHistoryManager.getInstance(this).addSearchQuery(query);
        if (containerSearchDiscovery != null) containerSearchDiscovery.setVisibility(View.GONE);
        if (query == null || query.isEmpty()) return;

        Matcher matcher = YOUTUBE.matcher(query);
        if (matcher.find() || query.startsWith("http://") || query.startsWith("https://")) {
            // Direct URL download
            startDownload(query, null);
        } else {
            // Perform native YouTube search with thumbnail list
            performYoutubeSearch(query);
        }
    }

    private void performYoutubeSearch(String query) {
        List<SearchResult> cached = searchCache.get(query.toLowerCase());
        if (cached != null) {
            txtSearchHint.setVisibility(View.GONE);
            txtSearchStatus.setText(cached.size() + " resultados");
            recyclerSearchResults.setVisibility(View.VISIBLE);
            searchResultAdapter.setResults(cached);
            refreshDownloadedBadges();
            return;
        }
        txtSearchHint.setVisibility(View.GONE);
        searchLoading.setVisibility(View.VISIBLE);
        txtSearchStatus.setText("Buscando en YouTube...");
        searchResultAdapter.setResults(Collections.emptyList());

        DescargadorApp.IO.execute(() -> {
            List<SearchResult> results = new ArrayList<>();
            try {
                // Ocho resultados planos reducen red y parseo sin perder relevancia.
                YoutubeDLRequest request = new YoutubeDLRequest("ytsearch8:" + query);
                request.addOption("--flat-playlist");
                request.addOption("--dump-json");
                request.addOption("--socket-timeout", "8");

                YoutubeDLResponse response = YoutubeDL.getInstance().execute(request);
                String out = response.getOut();

                if (out != null) {
                    String[] lines = out.split("\r?\n");
                    for (String line : lines) {
                        line = line.trim();
                        if (line.isEmpty() || !line.startsWith("{")) continue;
                        try {
                            JSONObject json = new JSONObject(line);
                            String id = json.optString("id", "");
                            String title = json.optString("title", "Sin título");
                            String uploader = json.optString("uploader", json.optString("channel", "YouTube"));
                            long duration = json.optLong("duration", 0);
                            String url = json.optString("url", "https://www.youtube.com/watch?v=" + id);
                            String thumb = "https://i.ytimg.com/vi/" + id + "/mqdefault.jpg";

                            if (!id.isEmpty()) {
                                results.add(new SearchResult(id, title, uploader, duration, thumb, url));
                            }
                        } catch (Exception ignored) {}
                    }
                }

                runOnUiThread(() -> {
                    searchLoading.setVisibility(View.GONE);
                    if (results.isEmpty()) {
                        txtSearchStatus.setText("No se encontraron resultados");
                        txtSearchHint.setText("Intenta con otros términos de búsqueda");
                        txtSearchHint.setVisibility(View.VISIBLE);
                        recyclerSearchResults.setVisibility(View.GONE);
                if (containerSearchDiscovery != null) {
                    containerSearchDiscovery.setVisibility(View.VISIBLE);
                    refreshDiscoveryContent();
                }
                    } else {
                        searchCache.put(query.toLowerCase(), new ArrayList<>(results));
                        txtSearchStatus.setText(results.size() + " resultados");
                        recyclerSearchResults.setVisibility(View.VISIBLE);
                        searchResultAdapter.setResults(results);
                        refreshDownloadedBadges();
                    }
                });

            } catch (Exception e) {
                runOnUiThread(() -> {
                    searchLoading.setVisibility(View.GONE);
                    txtSearchStatus.setText("Error en la búsqueda");
                    txtSearchHint.setText("Verifica tu conexión a internet");
                    txtSearchHint.setVisibility(View.VISIBLE);
                });
            }
        });
    }

    private void startDownload(String targetUrl, String defaultTitle) {
        startDownload(targetUrl, defaultTitle, extractVideoId(targetUrl));
    }

    private synchronized void startDownload(String targetUrl, String defaultTitle, String videoId) {
        if (downloading) {
            downloadQueue.offer(new DownloadJob(targetUrl, defaultTitle, videoId));
            Toast.makeText(this, "Añadida a la cola de descargas", Toast.LENGTH_SHORT).show();
            return;
        }

        File dir = StorageUtil.getDownloadDir(this);

        YoutubeDLRequest request = new YoutubeDLRequest(targetUrl);
        request.addOption("--no-playlist");
        request.addOption("--no-update");
        request.addOption("--extractor-args", "youtube:player_client=android,web");
        request.addOption("--no-mtime");
        request.addOption("--restrict-filenames");
        request.addOption("-o", new File(dir, "%(title).160s.%(ext)s").getAbsolutePath());

        if (isMp3) {
            request.addOption("-x");
            request.addOption("--audio-format", "mp3");
            request.addOption("--audio-quality", "192K");
            request.addOption("--embed-thumbnail");
            request.addOption("--add-metadata");
        } else {
            request.addOption("-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best");
            request.addOption("--merge-output-format", "mp4");
        }

        downloading = true;
        cardProgress.setVisibility(View.VISIBLE);
        progressBar.setProgress(0);
        txtStatus.setText(defaultTitle != null ? ("Descargando: " + defaultTitle) : "Iniciando descarga...");
        txtEta.setText("Conectando...");

        DescargadorApp.IO.execute(() -> {
            try {
                YoutubeDL.getInstance().execute(request, "mobile-dl", (percent, eta, line) -> {
                    runOnUiThread(() -> {
                        int p = Math.round(percent);
                        progressBar.setProgress(p);
                        txtStatus.setText("Descargando " + p + "%");
                        txtEta.setText("Faltan aprox. " + eta + " s");
                    });
                    return kotlin.Unit.INSTANCE;
                });

                runOnUiThread(() -> {
                    progressBar.setProgress(100);
                    txtStatus.setText("¡Descarga completada con éxito!");
                    txtEta.setText("Guardado en Descargas/Descargador");
                    Toast.makeText(this, "Guardado en tu biblioteca", Toast.LENGTH_SHORT).show();
                    StorageUtil.scanFile(this, dir);
                    if (videoId != null && !videoId.isEmpty()) {
                        getSharedPreferences("downloaded_videos", MODE_PRIVATE).edit().putBoolean(videoId, true).apply();
                    }
                    downloading = false;
                    refreshMusicLibrary();
                    refreshDownloadedBadges();
                    startNextQueuedDownload();

                    cardProgress.postDelayed(() -> {
                        if (!downloading) cardProgress.setVisibility(View.GONE);
                    }, 4000);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    txtStatus.setText("Error al descargar");
                    txtEta.setText(e.getLocalizedMessage() != null ? e.getLocalizedMessage() : "Fallo en yt-dlp");
                    downloading = false;
                    startNextQueuedDownload();
                });
            }
        });
    }

    private synchronized void startNextQueuedDownload() {
        DownloadJob next = downloadQueue.poll();
        if (next != null) startDownload(next.url, next.title, next.videoId);
    }

    private String extractVideoId(String value) {
        if (value == null) return null;
        Matcher m = YOUTUBE.matcher(value);
        return m.find() ? m.group(1) : (value.matches("[A-Za-z0-9_-]{11}") ? value : null);
    }

    private void refreshDownloadedBadges() {
        if (searchResultAdapter == null) return;
        Set<String> ids = new HashSet<>();
        for (String key : getSharedPreferences("downloaded_videos", MODE_PRIVATE).getAll().keySet()) ids.add(key);
        searchResultAdapter.setDownloadedIds(ids);
        Set<String> titles = new HashSet<>();
        for (Song song : allSongs) {
            titles.add(java.text.Normalizer.normalize(song.getTitle(), java.text.Normalizer.Form.NFD)
                    .replaceAll("\\p{M}", "").replaceAll("[^a-zA-Z0-9]", "").toLowerCase());
        }
        searchResultAdapter.setDownloadedTitles(titles);
    }

    private void showAddOnlineToPlaylistDialog(SearchResult result) {
        List<String> names = PlaylistManager.getInstance(this).getPlaylistNames();
        String[] arr = names.toArray(new String[0]);
        new AlertDialog.Builder(this).setTitle("Agregar a playlist").setItems(arr, (d, which) -> {
            String selected = arr[which];
            PlaylistManager manager = PlaylistManager.getInstance(this);
            boolean added = manager.addOnlineTrack(selected, result);
            Toast.makeText(this, added ? "Agregada a " + selected : "Ya estaba en " + selected, Toast.LENGTH_SHORT).show();
            if (added && manager.isAutoDownloadEnabled(selected)) {
                startDownload(result.getUrl(), result.getTitle(), result.getId());
            }
            searchResultAdapter.notifyDataSetChanged();
        }).setNegativeButton("Cancelar", null).show();
    }

    private void setupLibraryTab() {
        recyclerLibrary.setLayoutManager(new LinearLayoutManager(this));

        songAdapter = new SongAdapter(this, allSongs, new SongAdapter.OnSongClickListener() {
            @Override
            public void onSongClick(Song song, List<Song> queue, int position) {
                SearchHistoryManager.getInstance(MainActivity.this).recordPlayedSong(song);
                if ("YouTube".equals(song.getFolder())) {
                    String id = extractVideoId(song.getPath());
                    if (id == null) id = song.getPath();
                    PlayerManager.getInstance().playOnline(id, song.getTitle(), song.getArtist(),
                            "https://i.ytimg.com/vi/" + id + "/mqdefault.jpg",
                            "https://www.youtube.com/watch?v=" + id);
                    startActivity(new Intent(MainActivity.this, NowPlayingActivity.class));
                    return;
                }
                PlayerManager.getInstance().playSong(song, queue);
                Intent intent = new Intent(MainActivity.this, NowPlayingActivity.class);
                startActivity(intent);
            }

            @Override
            public void onFavoriteClick(Song song, int position) {
                if (currentLibraryMode == 2 && isViewingSubList) {
                    showPlaylistSongs("Favoritos");
                }
            }

            @Override
            public void onMenuClick(Song song, View anchor, int position) {
                showSongMenu(song, anchor);
            }
        });

        folderAdapter = new FolderAdapter(this, null, (folderName, songs) -> {
            isViewingSubList = true;
            btnBackLibrary.setVisibility(View.VISIBLE);
            txtLibraryTitle.setText(folderName);
            songAdapter.updateSongs(songs);
            recyclerLibrary.setAdapter(songAdapter);
            txtSongCount.setText(songs.size() + (songs.size() == 1 ? " canción" : " canciones"));
        });

        playlistAdapter = new PlaylistAdapter(this, null, new PlaylistAdapter.OnPlaylistClickListener() {
            @Override
            public void onPlaylistClick(String playlistName) {
                showPlaylistSongs(playlistName);
            }

            @Override
            public void onDeleteClick(String playlistName) {
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("Eliminar Playlist")
                        .setMessage("¿Deseas eliminar '" + playlistName + "'?")
                        .setPositiveButton("Eliminar", (d, w) -> {
                            PlaylistManager.getInstance(MainActivity.this).deletePlaylist(playlistName);
                            refreshPlaylistsView();
                        })
                        .setNegativeButton("Cancelar", null)
                        .show();
            }

            @Override
            public void onAutoDownloadChanged(String playlistName, boolean enabled) {
                if (!enabled) return;
                PlaylistManager manager = PlaylistManager.getInstance(MainActivity.this);
                int queued = 0;
                for (String entry : manager.getSongPaths(playlistName)) {
                    SearchResult result = manager.getOnlineTrack(entry);
                    if (result != null && !getSharedPreferences("downloaded_videos", MODE_PRIVATE)
                            .getBoolean(result.getId(), false)) {
                        startDownload(result.getUrl(), result.getTitle(), result.getId());
                        queued++;
                    }
                }
                Toast.makeText(MainActivity.this,
                        queued == 0 ? "La playlist ya está disponible" : queued + " descarga(s) en cola",
                        Toast.LENGTH_SHORT).show();
            }
        });

        recyclerLibrary.setAdapter(songAdapter);

        chipSongs.setOnClickListener(v -> setLibraryMode(0));
        chipFolders.setOnClickListener(v -> setLibraryMode(1));
        chipPlaylists.setOnClickListener(v -> setLibraryMode(2));

        btnBackLibrary.setOnClickListener(v -> {
            isViewingSubList = false;
            btnBackLibrary.setVisibility(View.GONE);
            txtLibraryTitle.setText("Mi Música");
            setLibraryMode(currentLibraryMode);
        });

        btnShuffleAll.setOnClickListener(v -> {
            if (!allSongs.isEmpty()) {
                List<Song> shuffled = new ArrayList<>(allSongs);
                Collections.shuffle(shuffled);
                PlayerManager.getInstance().playSong(shuffled.get(0), shuffled);
            } else {
                Toast.makeText(this, "No hay canciones para reproducir", Toast.LENGTH_SHORT).show();
            }
        });

        inputSearchLibrary.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                applyLibraryFilter(s != null ? s.toString() : "");
            }
            @Override public void afterTextChanged(Editable s) {}
        });

        btnNewPlaylist.setOnClickListener(v -> showCreatePlaylistDialog());
    }


    private void setSongFilter(int mode) {
        currentSongFilter = mode;
        int activeText = ContextCompat.getColor(this, R.color.chip_active_text);
        int inactiveText = ContextCompat.getColor(this, R.color.text_secondary);

        if (chipFilterAll != null) {
            chipFilterAll.setBackgroundResource(mode == 0 ? R.drawable.bg_chip_active : R.drawable.bg_chip_inactive);
            chipFilterAll.setTextColor(mode == 0 ? activeText : inactiveText);
        }
        if (chipFilterFavorites != null) {
            chipFilterFavorites.setBackgroundResource(mode == 1 ? R.drawable.bg_chip_active : R.drawable.bg_chip_inactive);
            chipFilterFavorites.setTextColor(mode == 1 ? activeText : inactiveText);
        }
        if (chipFilterRecent != null) {
            chipFilterRecent.setBackgroundResource(mode == 2 ? R.drawable.bg_chip_active : R.drawable.bg_chip_inactive);
            chipFilterRecent.setTextColor(mode == 2 ? activeText : inactiveText);
        }
        if (chipFilterAZ != null) {
            chipFilterAZ.setBackgroundResource(mode == 3 ? R.drawable.bg_chip_active : R.drawable.bg_chip_inactive);
            chipFilterAZ.setTextColor(mode == 3 ? activeText : inactiveText);
        }

        if (songAdapter != null) {
            songAdapter.setFilterMode(mode);
            updateLibraryCounter();
        }
    }

    private void applyLibraryFilter(String query) {
        if (btnClearLibraryFilter != null) {
            btnClearLibraryFilter.setVisibility(query.isEmpty() ? View.GONE : View.VISIBLE);
        }

        if (currentLibraryMode == 0 || isViewingSubList) {
            if (songAdapter != null) {
                songAdapter.filter(query);
                updateLibraryCounter();
            }
        } else if (currentLibraryMode == 1) {
            if (folderAdapter != null) {
                folderAdapter.filter(query);
                int count = folderAdapter.getDisplayedCount();
                txtSongCount.setText(count + (count == 1 ? " carpeta" : " carpetas"));
            }
        } else if (currentLibraryMode == 2) {
            if (playlistAdapter != null) {
                playlistAdapter.filter(query);
                int count = playlistAdapter.getDisplayedCount();
                txtSongCount.setText(count + (count == 1 ? " playlist" : " playlists"));
            }
        }
    }

    private void updateLibraryCounter() {
        if (songAdapter != null && txtSongCount != null) {
            int count = songAdapter.getItemCount();
            if (currentSongFilter == 1) {
                txtSongCount.setText(count + (count == 1 ? " favorita" : " favoritas"));
            } else {
                txtSongCount.setText(count + (count == 1 ? " canción" : " canciones"));
            }
        }
    }

    private void setLibraryMode(int mode) {
        currentLibraryMode = mode;
        isViewingSubList = false;
        btnBackLibrary.setVisibility(View.GONE);
        txtLibraryTitle.setText("Mi Música");
        fabNewPlaylist.setVisibility(mode == 2 ? View.VISIBLE : View.GONE);
        if (scrollLibraryFilters != null) {
            scrollLibraryFilters.setVisibility(mode == 0 ? View.VISIBLE : View.GONE);
        }

        int activeText = ContextCompat.getColor(this, R.color.chip_active_text);
        int inactiveText = ContextCompat.getColor(this, R.color.text_secondary);

        chipSongs.setBackgroundResource(mode == 0 ? R.drawable.bg_chip_active : R.drawable.bg_chip_inactive);
        chipSongs.setTextColor(mode == 0 ? activeText : inactiveText);

        chipFolders.setBackgroundResource(mode == 1 ? R.drawable.bg_chip_active : R.drawable.bg_chip_inactive);
        chipFolders.setTextColor(mode == 1 ? activeText : inactiveText);

        chipPlaylists.setBackgroundResource(mode == 2 ? R.drawable.bg_chip_active : R.drawable.bg_chip_inactive);
        chipPlaylists.setTextColor(mode == 2 ? activeText : inactiveText);

        if (mode == 0) {
            recyclerLibrary.setAdapter(songAdapter);
            songAdapter.updateSongs(allSongs);
            txtSongCount.setText(allSongs.size() + (allSongs.size() == 1 ? " canción" : " canciones"));
        } else if (mode == 1) {
            Map<String, List<Song>> folders = MusicScanner.groupByFolder(allSongs);
            folderAdapter.updateFolders(folders);
            recyclerLibrary.setAdapter(folderAdapter);
            txtSongCount.setText(folders.size() + (folders.size() == 1 ? " carpeta" : " carpetas"));
        } else {
            refreshPlaylistsView();
        }
    }

    private void refreshPlaylistsView() {
        List<String> list = PlaylistManager.getInstance(this).getPlaylistNames();
        playlistAdapter.updatePlaylists(list);
        recyclerLibrary.setAdapter(playlistAdapter);
        txtSongCount.setText(list.size() + (list.size() == 1 ? " playlist" : " playlists"));
    }

    private void showPlaylistSongs(String playlistName) {
        isViewingSubList = true;
        btnBackLibrary.setVisibility(View.VISIBLE);
        txtLibraryTitle.setText(playlistName);
        fabNewPlaylist.setVisibility(View.GONE);

        List<String> paths = PlaylistManager.getInstance(this).getSongPaths(playlistName);
        List<Song> songs = new ArrayList<>();
        for (Song s : allSongs) {
            if (paths.contains(s.getPath())) songs.add(s);
        }
        PlaylistManager manager = PlaylistManager.getInstance(this);
        for (String entry : paths) {
            SearchResult result = manager.getOnlineTrack(entry);
            if (result != null) {
                songs.add(new Song(System.currentTimeMillis(), result.getTitle(), result.getChannel(),
                        "YouTube", result.getDurationSeconds() * 1000L, result.getThumbnailUrl(),
                        result.getUrl(), System.currentTimeMillis()));
            }
        }

        songAdapter.updateSongs(songs);
        recyclerLibrary.setAdapter(songAdapter);
        txtSongCount.setText(songs.size() + (songs.size() == 1 ? " canción" : " canciones"));
    }

    private void showCreatePlaylistDialog() {
        EditText input = new EditText(this);
        input.setHint("Nombre de la playlist");
        input.setSingleLine(true);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        FrameLayout container = new FrameLayout(this);
        container.setPadding(pad, pad, pad, pad);
        container.addView(input);

        new AlertDialog.Builder(this)
                .setTitle("Nueva Playlist")
                .setView(container)
                .setPositiveButton("Crear", (d, w) -> {
                    String name = input.getText().toString().trim();
                    if (!name.isEmpty()) {
                        PlaylistManager.getInstance(this).createPlaylist(name);
                        refreshPlaylistsView();
                    }
                })
                .setNegativeButton("Cancelar", null)
                .show();
    }

    private void showSongMenu(Song song, View anchor) {
        PopupMenu popup = new PopupMenu(this, anchor);
        popup.getMenu().add("Añadir a playlist...");
        popup.getMenu().add("Compartir archivo");
        popup.getMenu().add("Eliminar del dispositivo");

        popup.setOnMenuItemClickListener(item -> {
            String title = item.getTitle().toString();
            if (title.startsWith("Añadir")) {
                showAddToPlaylistDialog(song);
            } else if (title.startsWith("Compartir")) {
                shareSong(song);
            } else if (title.startsWith("Eliminar")) {
                deleteSong(song);
            }
            return true;
        });
        popup.show();
    }

    private void showAddToPlaylistDialog(Song song) {
        List<String> names = PlaylistManager.getInstance(this).getPlaylistNames();
        if (names.isEmpty()) {
            Toast.makeText(this, "No tienes playlists creadas", Toast.LENGTH_SHORT).show();
            return;
        }
        String[] arr = names.toArray(new String[0]);
        new AlertDialog.Builder(this)
                .setTitle("Añadir a Playlist")
                .setItems(arr, (d, which) -> {
                    String selected = arr[which];
                    PlaylistManager.getInstance(this).addSongToPlaylist(selected, song.getPath());
                    Toast.makeText(this, "Añadida a " + selected, Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("Cancelar", null)
                .show();
    }

    private void shareSong(Song song) {
        try {
            File f = new File(song.getPath());
            Intent intent = new Intent(Intent.ACTION_SEND);
            intent.setType("audio/*");
            intent.putExtra(Intent.EXTRA_STREAM, Uri.fromFile(f));
            startActivity(Intent.createChooser(intent, "Compartir música"));
        } catch (Exception e) {
            Toast.makeText(this, "No se pudo compartir", Toast.LENGTH_SHORT).show();
        }
    }

    private void deleteSong(Song song) {
        new AlertDialog.Builder(this)
                .setTitle("Eliminar canción")
                .setMessage("¿Deseas eliminar permanentemente '" + song.getTitle() + "'?")
                .setPositiveButton("Eliminar", (d, w) -> {
                    try {
                        File f = new File(song.getPath());
                        if (f.exists()) f.delete();
                        refreshMusicLibrary();
                        Toast.makeText(this, "Canción eliminada", Toast.LENGTH_SHORT).show();
                    } catch (Exception e) {
                        Toast.makeText(this, "Error al eliminar", Toast.LENGTH_SHORT).show();
                    }
                })
                .setNegativeButton("Cancelar", null)
                .show();
    }

    private void setupMiniPlayer() {
        miniPlayerLayout.setOnClickListener(v -> {
            if (PlayerManager.getInstance().getCurrentSong() != null) {
                Intent intent = new Intent(MainActivity.this, NowPlayingActivity.class);
                startActivity(intent);
                overridePendingTransition(R.anim.slide_up, R.anim.fade_out);
            }
        });

        // Interactive Swipe / Drag UP with spring elasticity to expand
        miniPlayerLayout.setOnTouchListener((v, event) -> {
            switch (event.getAction()) {
                case MotionEvent.ACTION_DOWN:
                    miniPlayerTouchY = event.getRawY();
                    isDraggingMiniPlayer = false;
                    return false;
                case MotionEvent.ACTION_MOVE:
                    float deltaY = event.getRawY() - miniPlayerTouchY;
                    if (deltaY < -15) {
                        isDraggingMiniPlayer = true;
                        miniPlayerLayout.setTranslationY(deltaY * 0.7f); // Elastic drag up
                        return true;
                    }
                    break;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    if (isDraggingMiniPlayer) {
                        float finalDeltaY = event.getRawY() - miniPlayerTouchY;
                        if (finalDeltaY < -60) {
                            miniPlayerLayout.animate().translationY(0).setDuration(150).start();
                            if (PlayerManager.getInstance().getCurrentSong() != null) {
                                Intent intent = new Intent(MainActivity.this, NowPlayingActivity.class);
                                startActivity(intent);
                                overridePendingTransition(R.anim.slide_up, R.anim.fade_out);
                            }
                        } else {
                            // Spring bounce back down
                            miniPlayerLayout.animate()
                                    .translationY(0)
                                    .setDuration(300)
                                    .setInterpolator(new OvershootInterpolator(1.8f))
                                    .start();
                        }
                        return true;
                    }
                    break;
            }
            return false;
        });

        btnMiniPlayPause.setOnClickListener(v -> PlayerManager.getInstance().togglePlayPause());
        btnMiniNext.setOnClickListener(v -> PlayerManager.getInstance().playNext());
    }

    private void checkPermissionsAndScan() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        boolean alreadyAsked = prefs.getBoolean("all_permissions_requested_v1", false);

        if (!alreadyAsked) {
            prefs.edit().putBoolean("all_permissions_requested_v1", true).apply();
            List<String> permissions = new ArrayList<>();

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                permissions.add(Manifest.permission.READ_MEDIA_AUDIO);
                permissions.add(Manifest.permission.READ_MEDIA_VIDEO);
                permissions.add(Manifest.permission.READ_MEDIA_IMAGES);
            } else {
                permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE);
                permissions.add(Manifest.permission.WRITE_EXTERNAL_STORAGE);
            }

            List<String> needed = new ArrayList<>();
            for (String p : permissions) {
                if (ContextCompat.checkSelfPermission(this, p) != PackageManager.PERMISSION_GRANTED) {
                    needed.add(p);
                }
            }

            if (!needed.isEmpty()) {
                ActivityCompat.requestPermissions(this, needed.toArray(new String[0]), 101);
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && !Environment.isExternalStorageManager()) {
                try {
                    Intent intent = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
                    intent.setData(Uri.parse("package:" + getPackageName()));
                    startActivity(intent);
                } catch (Exception ignored) {}
            }
        }
        refreshMusicLibrary();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 101 && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            refreshMusicLibrary();
        }
    }

    private void refreshMusicLibrary() {
        DescargadorApp.IO.execute(() -> {
            List<Song> songs = MusicScanner.scanAllMusic(this);
            runOnUiThread(() -> {
                allSongs.clear();
                allSongs.addAll(songs);
                if (currentLibraryMode == 0 && !isViewingSubList) {
                    songAdapter.updateSongs(allSongs);
                    txtSongCount.setText(allSongs.size() + (allSongs.size() == 1 ? " canción" : " canciones"));
                }
            });
        });
    }

    private void handleIntent(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        String type = intent.getType();

        if (Intent.ACTION_SEND.equals(action) && "text/plain".equals(type)) {
            String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
            if (sharedText != null && !sharedText.trim().isEmpty()) {
                switchTab(true);
                inputSearch.setText(sharedText.trim());
                triggerSearchOrDownload(sharedText.trim());
            }
        }
    }

    private void hideKeyboard() {
        View view = getCurrentFocus();
        if (view != null) {
            InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) imm.hideSoftInputFromWindow(view.getWindowToken(), 0);
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshDiscoveryContent();
        PlayerManager.getInstance().addListener(this);
        updateMiniPlayer();
    }

    private void updateMiniPlayer() {
        if (miniPlayerLayout == null) return;
        Song current = PlayerManager.getInstance().getCurrentSong();
        if (current != null) {
            miniPlayerLayout.setVisibility(View.VISIBLE);
            miniPlayerLayout.setTranslationY(0f);
            if (txtMiniTitle != null) txtMiniTitle.setText(current.getTitle());
            if (txtMiniArtist != null) txtMiniArtist.setText(current.getArtist());
            if (imgMiniCover != null) {
                CoverArtLoader.getInstance().loadSongCover(current.getPath(), imgMiniCover);
            }
            if (btnMiniPlayPause != null) {
                btnMiniPlayPause.setImageResource(PlayerManager.getInstance().isPlaying() ? R.drawable.ic_pause : R.drawable.ic_play_arrow);
            }
            int pos = PlayerManager.getInstance().getCurrentPosition();
            int dur = PlayerManager.getInstance().getDuration();
            if (miniProgress != null) {
                miniProgress.setMax(dur > 0 ? dur : 100);
                miniProgress.setProgress(pos);
            }
        } else {
            miniPlayerLayout.setVisibility(View.GONE);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        PlayerManager.getInstance().removeListener(this);
    }

    @Override
    public void onTrackChanged(Song song) {
        runOnUiThread(() -> {
            updateMiniPlayer();
            if (songAdapter != null) songAdapter.notifyDataSetChanged();
        });
    }

    @Override
    public void onPlaybackStateChanged(boolean isPlaying) {
        runOnUiThread(() -> {
            if (btnMiniPlayPause != null) {
                btnMiniPlayPause.setImageResource(isPlaying ? R.drawable.ic_pause : R.drawable.ic_play_arrow);
            }
        });
    }

    @Override
    public void onProgressUpdate(int currentPos, int duration) {
        runOnUiThread(() -> {
            miniProgress.setMax(duration > 0 ? duration : 100);
            miniProgress.setProgress(currentPos);
        });
    }
}
