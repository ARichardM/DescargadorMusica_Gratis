package cl.arichard.descargador.player;

import android.app.Activity;
import android.graphics.Typeface;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;
import androidx.appcompat.app.AlertDialog;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.ItemTouchHelper;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import cl.arichard.descargador.DescargadorApp;
import cl.arichard.descargador.R;
import cl.arichard.descargador.data.MusicScanner;
import cl.arichard.descargador.data.PlaylistManager;
import cl.arichard.descargador.model.Song;
import cl.arichard.descargador.util.CoverArtLoader;
import com.google.android.material.bottomsheet.BottomSheetBehavior;
import com.google.android.material.bottomsheet.BottomSheetDialog;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.HashSet;
import java.util.Set;

/** One editable queue shared by local music, online tracks and both players. */
public final class QueueSheet implements PlayerManager.PlaybackListener {
    private final Activity activity;
    private final PlayerManager player = PlayerManager.getInstance();
    private final BottomSheetDialog dialog;
    private final QueueAdapter adapter = new QueueAdapter();
    private TextView heading, empty;
    private RecyclerView recycler;
    private ItemTouchHelper touchHelper;
    private boolean dragging;

    public static void show(Activity activity) { new QueueSheet(activity).open(); }
    private QueueSheet(Activity activity) {
        this.activity = activity; dialog = new BottomSheetDialog(activity);
    }
    private int dp(int value) { return Math.round(value * activity.getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size) {
        TextView text = new TextView(activity); text.setText(value); text.setTextSize(size);
        text.setTextColor(ContextCompat.getColor(activity, R.color.text_primary));
        text.setGravity(Gravity.CENTER_VERTICAL); return text;
    }
    private TextView button(String label, Runnable action) {
        TextView button = text(label, 14); button.setGravity(Gravity.CENTER);
        button.setMinHeight(dp(48)); button.setPadding(dp(12), 0, dp(12), 0);
        button.setTextColor(ContextCompat.getColor(activity, R.color.accent));
        button.setBackgroundResource(R.drawable.bg_text_button);
        button.setOnClickListener(v -> action.run());
        cl.arichard.descargador.util.SafeTap.install(button); return button;
    }
    private void open() {
        LinearLayout root = new LinearLayout(activity); root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(12), dp(8), dp(12), dp(20));
        root.setBackgroundColor(ContextCompat.getColor(activity, R.color.bg_primary));
        View handle = new View(activity); handle.setBackgroundColor(0x66888888);
        LinearLayout.LayoutParams handleParams = new LinearLayout.LayoutParams(dp(36), dp(4));
        handleParams.gravity = Gravity.CENTER_HORIZONTAL; root.addView(handle, handleParams);
        LinearLayout header = new LinearLayout(activity); header.setGravity(Gravity.CENTER_VERTICAL);
        heading = text("Cola de reproducción", 20); heading.setTypeface(null, Typeface.BOLD);
        header.addView(heading, new LinearLayout.LayoutParams(0, dp(56), 1));
        header.addView(button("Cerrar", dialog::dismiss)); root.addView(header);
        TextView hint = text("Mantén pulsado y arrastra para cambiar el orden", 12);
        hint.setTextColor(ContextCompat.getColor(activity, R.color.text_secondary)); root.addView(hint);
        empty = text("Tu cola está vacía. Agrega tus canciones favoritas.", 15);
        empty.setPadding(0, dp(24), 0, dp(24)); root.addView(empty);
        recycler = new RecyclerView(activity); recycler.setLayoutManager(new LinearLayoutManager(activity));
        recycler.setAdapter(adapter); root.addView(recycler, new LinearLayout.LayoutParams(-1, 0, 1));
        touchHelper = new ItemTouchHelper(new ItemTouchHelper.SimpleCallback(ItemTouchHelper.UP | ItemTouchHelper.DOWN, 0) {
            @Override public RecyclerView.ViewHolder chooseDropTarget(RecyclerView.ViewHolder selected,
                    List<RecyclerView.ViewHolder> targets, int x, int y) {
                // Swap as the row crosses its neighbour's centre, rather than requiring
                // the finger to travel beyond the neighbour's entire height.
                float center = y + selected.itemView.getHeight() / 2f;
                RecyclerView.ViewHolder closest = null; float distance = Float.MAX_VALUE;
                for (RecyclerView.ViewHolder target : targets) {
                    float delta = Math.abs(center - (target.itemView.getTop() + target.itemView.getHeight() / 2f));
                    if (delta < distance) { distance = delta; closest = target; }
                }
                return closest;
            }
            @Override public boolean onMove(RecyclerView view, RecyclerView.ViewHolder from, RecyclerView.ViewHolder to) {
                int a = from.getBindingAdapterPosition(), b = to.getBindingAdapterPosition();
                if (a < 0 || b < 0) return false;
                player.moveQueueItem(a, b); adapter.notifyItemMoved(a, b); return true;
            }
            @Override public void onSwiped(RecyclerView.ViewHolder holder, int direction) {}
            @Override public void onSelectedChanged(RecyclerView.ViewHolder holder, int state) {
                dragging = state != ItemTouchHelper.ACTION_STATE_IDLE;
                dialog.getBehavior().setDraggable(!dragging);
                super.onSelectedChanged(holder, state);
            }
            @Override public void clearView(RecyclerView view, RecyclerView.ViewHolder holder) {
                super.clearView(view, holder); dragging = false; dialog.getBehavior().setDraggable(true);
                view.getParent().requestDisallowInterceptTouchEvent(false); refresh();
            }
        });
        touchHelper.attachToRecyclerView(recycler);
        recycler.setNestedScrollingEnabled(true);
        LinearLayout footer = new LinearLayout(activity);
        LinearLayout.LayoutParams addParams = new LinearLayout.LayoutParams(0, dp(52), 1); addParams.setMargins(0, dp(8), dp(4), 0);
        LinearLayout.LayoutParams clearParams = new LinearLayout.LayoutParams(0, dp(52), 1); clearParams.setMargins(dp(4), dp(8), 0, 0);
        footer.addView(button("＋ Agregar canciones", this::chooseSongs), addParams);
        footer.addView(button("Limpiar cola", () -> player.clearUpcoming()), clearParams); root.addView(footer);
        dialog.setContentView(root);
        root.getLayoutParams().height = Math.round(activity.getResources().getDisplayMetrics().heightPixels * .78f);
        dialog.getBehavior().setState(BottomSheetBehavior.STATE_EXPANDED);
        dialog.setOnDismissListener(v -> player.removeListener(this));
        player.addListener(this); refresh(); dialog.show();
        recycler.scrollToPosition(Math.max(0, player.getCurrentIndex()));
    }
    private void refresh() {
        if (dragging) return;
        recycler.post(() -> {
            if (dragging) return;
            adapter.notifyDataSetChanged();
            int count = player.getQueue().size();
            heading.setText("Cola · " + count); empty.setVisibility(count == 0 ? View.VISIBLE : View.GONE);
        });
    }
    @Override public void onQueueChanged() { refresh(); }
    @Override public void onTrackChanged(Song song) { refresh(); }
    @Override public void onPlaybackStateChanged(boolean playing) { refresh(); }
    @Override public void onProgressUpdate(int position, int duration) {}

    private void chooseSongs() {
        DescargadorApp.IO.execute(() -> {
            List<Song> library = MusicScanner.scanAllMusic(activity);
            Map<String, Song> choices = new LinkedHashMap<>();
            for (Song song : library) choices.put(song.getPath(), song);
            PlaylistManager manager = PlaylistManager.getInstance(activity);
            for (String name : manager.getPlaylistNames()) for (Song song : manager.resolveSongs(name, library))
                choices.put(song.getPath(), song);
            activity.runOnUiThread(() -> {
                if (activity.isFinishing() || activity.isDestroyed() || !dialog.isShowing()) return;
                showPicker(new ArrayList<>(choices.values()));
            });
        });
    }
    private void showPicker(List<Song> choices) {
        LinearLayout content = new LinearLayout(activity); content.setOrientation(LinearLayout.VERTICAL);
        EditText search = new EditText(activity); search.setHint("Buscar en tu música y playlists"); search.setSingleLine(true);
        content.addView(search);
        ListView list = new ListView(activity); list.setChoiceMode(ListView.CHOICE_MODE_MULTIPLE);
        content.addView(list, new LinearLayout.LayoutParams(-1, dp(300)));
        Set<String> selected = new HashSet<>(); List<Song> visible = new ArrayList<>();
        ArrayAdapter<String> labels = new ArrayAdapter<>(activity, android.R.layout.simple_list_item_multiple_choice);
        list.setAdapter(labels);
        Runnable filter = () -> {
            visible.clear(); labels.clear();
            String query = search.getText().toString().toLowerCase(Locale.ROOT);
            for (Song song : choices) if ((song.getTitle() + " " + song.getArtist()).toLowerCase(Locale.ROOT).contains(query)) {
                visible.add(song); labels.add(song.getTitle() + " · " + song.getArtist());
            }
            list.clearChoices();
            for (int i = 0; i < visible.size(); i++) list.setItemChecked(i, selected.contains(visible.get(i).getPath()));
        };
        list.setOnItemClickListener((parent, view, position, id) -> {
            String key = visible.get(position).getPath();
            if (list.isItemChecked(position)) selected.add(key); else selected.remove(key);
        });
        search.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) { filter.run(); }
            @Override public void afterTextChanged(Editable s) {}
        });
        filter.run();
        new AlertDialog.Builder(activity).setTitle(choices.isEmpty() ? "Agrega música o guarda canciones en una playlist" : "Agregar a la cola")
                .setView(content).setNegativeButton("Cancelar", null).setPositiveButton("Agregar", (d, which) -> {
                    for (Song song : choices) if (selected.contains(song.getPath())) player.enqueue(song, false);
                }).show();
    }

    private class QueueAdapter extends RecyclerView.Adapter<QueueHolder> {
        @Override public QueueHolder onCreateViewHolder(ViewGroup parent, int type) {
            LinearLayout row = new LinearLayout(activity); row.setGravity(Gravity.CENTER_VERTICAL);
            row.setLayoutParams(new RecyclerView.LayoutParams(-1, -2));
            row.setPadding(0, dp(6), 0, dp(6));
            ImageView cover = new ImageView(activity); cover.setScaleType(ImageView.ScaleType.CENTER_CROP);
            row.addView(cover, new LinearLayout.LayoutParams(dp(44), dp(44)));
            TextView title = text("", 14); title.setMaxLines(2); title.setPadding(dp(10), 0, dp(4), 0);
            row.addView(title, new LinearLayout.LayoutParams(0, dp(54), 1));
            TextView remove = button("×", () -> {}); remove.setTextSize(24); remove.setContentDescription("Quitar de la cola");
            row.addView(remove, new LinearLayout.LayoutParams(dp(44), dp(48)));
            TextView drag = text("≡", 24); drag.setGravity(Gravity.CENTER); drag.setContentDescription("Arrastrar para reordenar");
            row.addView(drag, new LinearLayout.LayoutParams(dp(44), dp(48)));
            return new QueueHolder(row, cover, title, remove, drag);
        }
        @Override public void onBindViewHolder(QueueHolder holder, int position) {
            Song song = player.getQueue().get(position);
            boolean active = position == player.getCurrentIndex();
            holder.title.setText((active ? "Ahora · " : "") + song.getTitle() + "\n" + song.getArtist());
            holder.title.setTextColor(ContextCompat.getColor(activity, active ? R.color.accent : R.color.text_primary));
            holder.itemView.setBackgroundResource(active ? R.drawable.bg_song_playing : 0);
            CoverArtLoader.getInstance().loadSongCover(song.getCoverPath(), holder.cover);
            holder.itemView.setOnClickListener(v -> player.playQueueIndex(holder.getBindingAdapterPosition()));
            cl.arichard.descargador.util.SafeTap.installRowTap(holder.itemView);
            holder.remove.setOnClickListener(v -> player.removeQueueItem(holder.getBindingAdapterPosition()));
            holder.drag.setOnTouchListener((v, event) -> {
                if (event.getActionMasked() == MotionEvent.ACTION_DOWN) {
                    recycler.getParent().requestDisallowInterceptTouchEvent(true);
                    touchHelper.startDrag(holder);
                }
                return true;
            });
        }
        @Override public int getItemCount() { return player.getQueue().size(); }
    }
    private static class QueueHolder extends RecyclerView.ViewHolder {
        final ImageView cover; final TextView title, remove, drag;
        QueueHolder(View view, ImageView cover, TextView title, TextView remove, TextView drag) {
            super(view); this.cover = cover; this.title = title; this.remove = remove; this.drag = drag;
        }
    }
}
