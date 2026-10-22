package cl.arichard.descargador.data;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.HashSet;
import java.util.Set;
import cl.arichard.descargador.model.SearchResult;

public class PlaylistManager {
    private static PlaylistManager instance;
    private final File storageFile;
    private final Map<String, List<String>> playlists = new HashMap<>();
    private final Map<String, SearchResult> onlineTracks = new HashMap<>();
    private final Set<String> autoDownloadPlaylists = new HashSet<>();

    private PlaylistManager(Context context) {
        this.storageFile = new File(context.getFilesDir(), "playlists.json");
        load();
        if (!playlists.containsKey("Favoritos")) {
            playlists.put("Favoritos", new ArrayList<>());
            save();
        }
    }

    public static synchronized PlaylistManager getInstance(Context context) {
        if (instance == null) {
            instance = new PlaylistManager(context.getApplicationContext());
        }
        return instance;
    }

    private void load() {
        playlists.clear();
        if (!storageFile.exists()) return;
        try (FileInputStream fis = new FileInputStream(storageFile)) {
            byte[] data = new byte[(int) storageFile.length()];
            fis.read(data);
            String jsonStr = new String(data, StandardCharsets.UTF_8);
            JSONObject root = new JSONObject(jsonStr);
            JSONObject listsRoot = root.optJSONObject("playlists");
            if (listsRoot == null) listsRoot = root; // Compatibilidad con v2.0
            JSONArray names = listsRoot.names();
            if (names != null) {
                for (int i = 0; i < names.length(); i++) {
                    String name = names.getString(i);
                    if ("onlineTracks".equals(name) || "autoDownload".equals(name)) continue;
                    JSONArray arr = listsRoot.optJSONArray(name);
                    if (arr == null) continue;
                    List<String> paths = new ArrayList<>();
                    for (int j = 0; j < arr.length(); j++) {
                        paths.add(arr.getString(j));
                    }
                    playlists.put(name, paths);
                }
            }
            JSONObject tracks = root.optJSONObject("onlineTracks");
            if (tracks != null) {
                JSONArray ids = tracks.names();
                if (ids != null) for (int i = 0; i < ids.length(); i++) {
                    String id = ids.getString(i);
                    JSONObject item = tracks.getJSONObject(id);
                    onlineTracks.put(id, new SearchResult(id, item.optString("title"),
                            item.optString("channel"), item.optLong("duration"),
                            item.optString("thumbnail"), item.optString("url")));
                }
            }
            JSONArray auto = root.optJSONArray("autoDownload");
            if (auto != null) for (int i = 0; i < auto.length(); i++) autoDownloadPlaylists.add(auto.getString(i));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void save() {
        try (FileOutputStream fos = new FileOutputStream(storageFile)) {
            JSONObject root = new JSONObject();
            JSONObject lists = new JSONObject();
            for (Map.Entry<String, List<String>> entry : playlists.entrySet()) {
                JSONArray arr = new JSONArray(entry.getValue());
                lists.put(entry.getKey(), arr);
            }
            root.put("playlists", lists);
            JSONObject tracks = new JSONObject();
            for (Map.Entry<String, SearchResult> entry : onlineTracks.entrySet()) {
                SearchResult r = entry.getValue();
                JSONObject item = new JSONObject();
                item.put("title", r.getTitle()); item.put("channel", r.getChannel());
                item.put("duration", r.getDurationSeconds()); item.put("thumbnail", r.getThumbnailUrl());
                item.put("url", r.getUrl()); tracks.put(entry.getKey(), item);
            }
            root.put("onlineTracks", tracks);
            root.put("autoDownload", new JSONArray(autoDownloadPlaylists));
            fos.write(root.toString().getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public synchronized List<String> getPlaylistNames() {
        List<String> list = new ArrayList<>();
        list.add("Favoritos");
        for (String name : playlists.keySet()) {
            if (!"Favoritos".equalsIgnoreCase(name)) {
                list.add(name);
            }
        }
        return list;
    }

    public synchronized List<String> getSongPaths(String playlistName) {
        List<String> list = playlists.get(playlistName);
        return list != null ? new ArrayList<>(list) : new ArrayList<>();
    }

    public synchronized boolean createPlaylist(String name) {
        if (name == null || name.trim().isEmpty() || playlists.containsKey(name.trim())) {
            return false;
        }
        playlists.put(name.trim(), new ArrayList<>());
        save();
        return true;
    }

    public synchronized boolean deletePlaylist(String name) {
        if ("Favoritos".equalsIgnoreCase(name)) return false;
        if (playlists.remove(name) != null) {
            autoDownloadPlaylists.remove(name);
            save();
            return true;
        }
        return false;
    }

    public synchronized boolean addOnlineTrack(String playlistName, SearchResult result) {
        if (result == null) return false;
        onlineTracks.put(result.getId(), result);
        boolean added = addSongToPlaylist(playlistName, "youtube:" + result.getId());
        save();
        return added;
    }

    public synchronized SearchResult getOnlineTrack(String entry) {
        if (entry == null || !entry.startsWith("youtube:")) return null;
        return onlineTracks.get(entry.substring("youtube:".length()));
    }

    public synchronized boolean isOnlineTrackInPlaylist(String playlistName, String videoId) {
        List<String> list = playlists.get(playlistName);
        return list != null && list.contains("youtube:" + videoId);
    }

    public synchronized boolean isAutoDownloadEnabled(String playlistName) {
        return autoDownloadPlaylists.contains(playlistName);
    }

    public synchronized void setAutoDownloadEnabled(String playlistName, boolean enabled) {
        if (enabled) autoDownloadPlaylists.add(playlistName); else autoDownloadPlaylists.remove(playlistName);
        save();
    }

    public synchronized boolean addSongToPlaylist(String playlistName, String songPath) {
        List<String> list = playlists.get(playlistName);
        if (list == null) {
            list = new ArrayList<>();
            playlists.put(playlistName, list);
        }
        if (!list.contains(songPath)) {
            list.add(songPath);
            save();
            return true;
        }
        return false;
    }

    public synchronized boolean removeSongFromPlaylist(String playlistName, String songPath) {
        List<String> list = playlists.get(playlistName);
        if (list != null && list.remove(songPath)) {
            save();
            return true;
        }
        return false;
    }

    public synchronized boolean isFavorite(String songPath) {
        List<String> favs = playlists.get("Favoritos");
        return favs != null && favs.contains(songPath);
    }

    public synchronized void removeSongEverywhere(String path) {
        for (List<String> entries : playlists.values()) entries.remove(path);
        if (path.startsWith("youtube:")) onlineTracks.remove(path.substring(8));
        save();
    }

    public synchronized List<cl.arichard.descargador.model.Song> resolveSongs(String name,
            List<cl.arichard.descargador.model.Song> library) {
        List<cl.arichard.descargador.model.Song> songs = new ArrayList<>();
        for (String entry : getSongPaths(name)) {
            SearchResult result = getOnlineTrack(entry);
            if (result != null) {
                songs.add(new cl.arichard.descargador.model.Song(0, result.getTitle(), result.getChannel(),
                        "YouTube", result.getDurationSeconds() * 1000L, entry, "YouTube", 0));
            } else {
                for (cl.arichard.descargador.model.Song song : library)
                    if (entry.equals(song.getPath())) { songs.add(song); break; }
            }
        }
        return songs;
    }

    public synchronized boolean toggleFavorite(String songPath) {
        if (isFavorite(songPath)) {
            removeSongFromPlaylist("Favoritos", songPath);
            return false;
        } else {
            addSongToPlaylist("Favoritos", songPath);
            return true;
        }
    }
}
