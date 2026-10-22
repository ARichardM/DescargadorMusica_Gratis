package cl.arichard.descargador.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import cl.arichard.descargador.R;
import cl.arichard.descargador.model.SearchResult;
import cl.arichard.descargador.util.ImageLoader;
import cl.arichard.descargador.data.PlaylistManager;
import java.util.HashSet;
import java.util.Set;
import java.util.ArrayList;
import java.util.List;

public class SearchResultAdapter extends RecyclerView.Adapter<SearchResultAdapter.ViewHolder> {

    public interface OnResultClickListener {
        void onAddClick(SearchResult result, View anchor);
        void onPlayClick(SearchResult result);
        void onFavoriteChanged(SearchResult result, boolean favorite);
        void onItemClick(SearchResult result);
    }

    private final Context context;
    private final List<SearchResult> results = new ArrayList<>();
    private final OnResultClickListener listener;
    private final Set<String> downloadedIds = new HashSet<>();
    private final Set<String> downloadedTitles = new HashSet<>();

    public SearchResultAdapter(Context context, OnResultClickListener listener) {
        this.context = context;
        this.listener = listener;
    }

    public void setDownloadedIds(Set<String> ids) {
        downloadedIds.clear();
        if (ids != null) downloadedIds.addAll(ids);
        notifyDataSetChanged();
    }

    public void setDownloadedTitles(Set<String> titles) {
        downloadedTitles.clear();
        if (titles != null) downloadedTitles.addAll(titles);
        notifyDataSetChanged();
    }

    private String normalize(String value) {
        return value == null ? "" : java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "").replaceAll("[^a-zA-Z0-9]", "").toLowerCase();
    }

    public void setResults(List<SearchResult> newResults) {
        results.clear();
        if (newResults != null) {
            results.addAll(newResults);
        }
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(context).inflate(R.layout.item_search_result, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
        SearchResult item = results.get(position);
        holder.txtTitle.setText(item.getTitle());
        holder.txtChannel.setText(item.getChannel() + " • " + item.getFormattedDuration());

        ImageLoader.getInstance().load(item.getThumbnailUrl(), holder.imgThumbnail);

        holder.imgDownloaded.setVisibility(downloadedIds.contains(item.getId()) || downloadedTitles.contains(normalize(item.getTitle()))
                ? View.VISIBLE : View.GONE);
        boolean favorite = PlaylistManager.getInstance(context).isOnlineTrackInPlaylist("Favoritos", item.getId());
        holder.btnFavorite.setImageResource(favorite ? R.drawable.ic_favorite_filled : R.drawable.ic_favorite);

        holder.btnAdd.setOnClickListener(v -> {
            if (listener != null) listener.onAddClick(item, holder.btnAdd);
        });

        holder.btnPlay.setOnClickListener(v -> { if (listener != null) listener.onPlayClick(item); });
        holder.btnFavorite.setOnClickListener(v -> {
            PlaylistManager pm = PlaylistManager.getInstance(context);
            boolean exists = pm.isOnlineTrackInPlaylist("Favoritos", item.getId());
            if (exists) pm.removeSongFromPlaylist("Favoritos", "youtube:" + item.getId());
            else pm.addOnlineTrack("Favoritos", item);
            if (listener != null) listener.onFavoriteChanged(item, !exists);
            notifyItemChanged(holder.getBindingAdapterPosition());
        });

        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onItemClick(item);
        });
    }

    @Override
    public int getItemCount() {
        return results.size();
    }

    static class ViewHolder extends RecyclerView.ViewHolder {
        ImageView imgThumbnail;
        TextView txtTitle;
        TextView txtChannel;
        FrameLayout btnAdd;
        ImageView btnPlay, btnFavorite, imgDownloaded;

        public ViewHolder(@NonNull View itemView) {
            super(itemView);
            imgThumbnail = itemView.findViewById(R.id.imgThumbnail);
            txtTitle = itemView.findViewById(R.id.txtResultTitle);
            txtChannel = itemView.findViewById(R.id.txtResultChannel);
            btnAdd = itemView.findViewById(R.id.btnAddResult);
            btnPlay = itemView.findViewById(R.id.btnPlayResult);
            btnFavorite = itemView.findViewById(R.id.btnFavoriteResult);
            imgDownloaded = itemView.findViewById(R.id.imgDownloadedResult);
        }
    }
}
