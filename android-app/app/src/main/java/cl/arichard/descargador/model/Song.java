package cl.arichard.descargador.model;

import org.json.JSONException;
import org.json.JSONObject;
import java.io.Serializable;

public class Song implements Serializable {
    private long id;
    private String title;
    private String artist;
    private String album;
    private long duration;
    private String path;
    private String folder;
    private long dateAdded;

    public Song(long id, String title, String artist, String album, long duration, String path, String folder, long dateAdded) {
        this.id = id;
        this.title = (title != null && !title.trim().isEmpty()) ? title.trim() : "Canción sin título";
        this.artist = (artist != null && !artist.trim().isEmpty() && !artist.equals("<unknown>")) ? artist.trim() : "Artista desconocido";
        this.album = (album != null && !album.trim().isEmpty()) ? album.trim() : "Álbum desconocido";
        this.duration = duration;
        this.path = path;
        this.folder = (folder != null && !folder.trim().isEmpty()) ? folder : "Descargas";
        this.dateAdded = dateAdded;
    }

    public long getId() { return id; }
    public String getTitle() { return title; }
    public String getArtist() { return artist; }
    public String getAlbum() { return album; }
    public long getDuration() { return duration; }
    public String getPath() { return path; }
    public String getFolder() { return folder; }
    public long getDateAdded() { return dateAdded; }

    public String getFormattedDuration() {
        if (duration <= 0) return "--:--";
        long totalSecs = duration / 1000;
        long mins = totalSecs / 60;
        long secs = totalSecs % 60;
        return String.format("%02d:%02d", mins, secs);
    }

    public JSONObject toJson() {
        JSONObject obj = new JSONObject();
        try {
            obj.put("id", id);
            obj.put("title", title);
            obj.put("artist", artist);
            obj.put("album", album);
            obj.put("duration", duration);
            obj.put("path", path);
            obj.put("folder", folder);
            obj.put("dateAdded", dateAdded);
        } catch (JSONException ignored) {}
        return obj;
    }

    public static Song fromJson(JSONObject obj) {
        return new Song(
            obj.optLong("id", System.currentTimeMillis()),
            obj.optString("title", "Canción"),
            obj.optString("artist", "Artista desconocido"),
            obj.optString("album", ""),
            obj.optLong("duration", 0),
            obj.optString("path", ""),
            obj.optString("folder", "Descargas"),
            obj.optLong("dateAdded", 0)
        );
    }
}
