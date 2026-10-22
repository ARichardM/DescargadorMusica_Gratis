package cl.arichard.descargador.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.RecyclerView;
import cl.arichard.descargador.R;
import cl.arichard.descargador.data.PlaylistManager;
import cl.arichard.descargador.model.Song;
import cl.arichard.descargador.player.PlayerManager;
import cl.arichard.descargador.util.CoverArtLoader;
import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

public class SongAdapter extends RecyclerView.Adapter<SongAdapter.SongViewHolder> {

    public interface OnSongClickListener {
        void onSongClick(Song song, List<Song> queue, int position);
        void onFavoriteClick(Song song, int position);
        void onMenuClick(Song song, View anchor, int position);
    }

    private final Context context;
    private final List<Song> originalList = new ArrayList<>();
    private final List<Song> displayedList = new ArrayList<>();
    private final OnSongClickListener listener;

    private String currentQuery = "";
    private int currentFilterMode = 0; // 0=All, 1=Favorites, 2=Recent, 3=A-Z

    public SongAdapter(Context context, List<Song> songs, OnSongClickListener listener) {
        this.context = context;
        this.listener = listener;
        setHasStableIds(true);
        updateSongs(songs);
    }

    public void updateSongs(List<Song> songs) {
        originalList.clear();
        if (songs != null) {
            originalList.addAll(songs);
        }
        applyFiltersAndSort();
    }

    public void setFilterMode(int mode) {
        this.currentFilterMode = mode;
        applyFiltersAndSort();
    }

    public void filter(String query) {
        this.currentQuery = query != null ? query.trim().toLowerCase() : "";
        applyFiltersAndSort();
    }

    private void applyFiltersAndSort() {
        List<Song> before = new ArrayList<>(displayedList);
        displayedList.clear();
        PlaylistManager pm = PlaylistManager.getInstance(context);

        for (Song s : originalList) {
            // Check favorite filter
            if (currentFilterMode == 1 && !pm.isFavorite(s.getPath())) {
                continue;
            }

            // Check text query filter
            if (!currentQuery.isEmpty()) {
                boolean matchTitle = s.getTitle().toLowerCase().contains(currentQuery);
                boolean matchArtist = s.getArtist().toLowerCase().contains(currentQuery);
                boolean matchAlbum = s.getAlbum() != null && s.getAlbum().toLowerCase().contains(currentQuery);
                if (!matchTitle && !matchArtist && !matchAlbum) {
                    continue;
                }
            }

            displayedList.add(s);
        }

        // Apply sorting
        if (currentFilterMode == 2) {
            // Recientes (date added descending)
            Collections.sort(displayedList, (a, b) -> Long.compare(b.getDateAdded(), a.getDateAdded()));
        } else if (currentFilterMode == 3) {
            // A - Z
            Collections.sort(displayedList, (a, b) -> a.getTitle().compareToIgnoreCase(b.getTitle()));
        }

        List<Song> after = new ArrayList<>(displayedList);
        androidx.recyclerview.widget.DiffUtil.calculateDiff(new androidx.recyclerview.widget.DiffUtil.Callback() {
            @Override public int getOldListSize() { return before.size(); }
            @Override public int getNewListSize() { return after.size(); }
            @Override public boolean areItemsTheSame(int a, int b) { return before.get(a).getPath().equals(after.get(b).getPath()); }
            @Override public boolean areContentsTheSame(int a, int b) {
                Song old = before.get(a), next = after.get(b);
                return old.getTitle().equals(next.getTitle()) && old.getArtist().equals(next.getArtist()) && old.getDuration() == next.getDuration();
            }
        }).dispatchUpdatesTo(this);
    }
    @Override public long getItemId(int position) {
        long id = 0xcbf29ce484222325L;
        for (char value : displayedList.get(position).getPath().toCharArray()) id = (id ^ value) * 0x100000001b3L;
        return id;
    }

    public List<Song> getDisplayedList() { return displayedList; }

    @NonNull @Override
    public SongViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(context).inflate(R.layout.item_song, parent, false);
        return new SongViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull SongViewHolder holder, int position) {
        Song song = displayedList.get(position);
        holder.txtTitle.setText(song.getTitle());
        holder.txtSubtitle.setText(song.getArtist() + " • " + song.getFormattedDuration());

        CoverArtLoader.getInstance().loadSongCover(song.getCoverPath(), holder.imgCover);

        boolean isLocalFile = song.getPath() != null && new File(song.getPath()).exists();
        if (holder.imgDownloadedBadge != null) {
            holder.imgDownloadedBadge.setVisibility(isLocalFile ? View.VISIBLE : View.GONE);
        }

        Song current = PlayerManager.getInstance().getCurrentSong();
        boolean isPlayingThis = current != null && current.getPath() != null && current.getPath().equals(song.getPath());

        int accentColor = ContextCompat.getColor(holder.itemView.getContext(), R.color.accent);
        int primaryTextColor = ContextCompat.getColor(holder.itemView.getContext(), R.color.text_primary);

        holder.itemView.setBackgroundResource(isPlayingThis ? R.drawable.bg_song_playing : 0);
        holder.imgIndicator.setImageResource(PlayerManager.getInstance().isPlaying() ? R.drawable.ic_pause : R.drawable.ic_play_arrow);
        holder.itemView.setContentDescription(song.getTitle() + (isPlayingThis ? " · Canción actual" : ""));
        if (isPlayingThis) {
            holder.txtTitle.setTextColor(accentColor);
            holder.viewPlayingOverlay.setVisibility(View.VISIBLE);
            holder.imgIndicator.setVisibility(View.VISIBLE);
        } else {
            holder.txtTitle.setTextColor(primaryTextColor);
            holder.viewPlayingOverlay.setVisibility(View.GONE);
            holder.imgIndicator.setVisibility(View.GONE);
        }

        boolean fav = PlaylistManager.getInstance(context).isFavorite(song.getPath());
        holder.btnFavorite.setImageResource(fav ? R.drawable.ic_favorite_filled : R.drawable.ic_favorite);

        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onSongClick(song, displayedList, position);
        });

        holder.btnFavorite.setOnClickListener(v -> {
            boolean nowFav = PlaylistManager.getInstance(context).toggleFavorite(song.getPath());
            holder.btnFavorite.setImageResource(nowFav ? R.drawable.ic_favorite_filled : R.drawable.ic_favorite);
            if (listener != null) listener.onFavoriteClick(song, position);
        });

        holder.btnMenu.setOnClickListener(v -> {
            if (listener != null) listener.onMenuClick(song, holder.btnMenu, position);
        });
        cl.arichard.descargador.util.SafeTap.install(holder.btnMenu);
        cl.arichard.descargador.util.SafeTap.install(holder.btnFavorite);
        cl.arichard.descargador.util.SafeTap.installRowTap(holder.itemView);
    }

    @Override public int getItemCount() { return displayedList.size(); }

    static class SongViewHolder extends RecyclerView.ViewHolder {
        TextView txtTitle, txtSubtitle;
        ImageView imgCover, imgIndicator, btnFavorite, btnMenu, imgDownloadedBadge;
        View viewPlayingOverlay;

        public SongViewHolder(@NonNull View itemView) {
            super(itemView);
            txtTitle = itemView.findViewById(R.id.txtSongTitle);
            txtSubtitle = itemView.findViewById(R.id.txtSongSubtitle);
            imgCover = itemView.findViewById(R.id.imgSongCover);
            imgIndicator = itemView.findViewById(R.id.imgPlayingIndicator);
            viewPlayingOverlay = itemView.findViewById(R.id.viewPlayingOverlay);
            btnFavorite = itemView.findViewById(R.id.btnFavorite);
            btnMenu = itemView.findViewById(R.id.btnSongMenu);
            imgDownloadedBadge = itemView.findViewById(R.id.imgDownloadedBadge);
        }
    }
}
