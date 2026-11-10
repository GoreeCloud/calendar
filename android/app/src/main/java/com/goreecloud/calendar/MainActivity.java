package com.goreecloud.calendar;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DatePickerDialog;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Native Android development client for user-controlled GoreeCloud Calendar.
 * HTTPS-only requests; session credentials stay in memory, never preferences.
 * This is not an offline-enabled or production security-reviewed application.
 */
public final class MainActivity extends Activity {
    private static final int CANVAS = Color.rgb(245,247,252);
    private static final int SURFACE = Color.WHITE;
    private static final int TEXT = Color.rgb(24,35,64);
    private static final int SOFT = Color.rgb(101,114,139);
    private static final int ACCENT = Color.rgb(77,92,200);
    private static final int OUTLINE = Color.rgb(226,232,241);

    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private String origin, sessionToken;
    private String selectedCalendarId;
    private LocalDate selectedDate = LocalDate.now();
    private LinearLayout body;
    private LinearLayout rootLayout;
    private LinearLayout resultContainer;
    private TextView status;
    private String activeTab = "agenda";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(CANVAS);
        getWindow().setNavigationBarColor(CANVAS);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
                | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        renderLogin();
    }

    @Override protected void onDestroy() {
        worker.shutdownNow();
        super.onDestroy();
    }

    private int dp(float size) {
        return Math.round(size * getResources().getDisplayMetrics().density);
    }

    private GradientDrawable shape(int color, int radius) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radius));
        return drawable;
    }

    private LinearLayout column() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        return layout;
    }

    private LinearLayout row() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.HORIZONTAL);
        layout.setGravity(Gravity.CENTER_VERTICAL);
        return layout;
    }

    private TextView text(String title, int size, boolean bold) {
        TextView view = new TextView(this);
        view.setText(title);
        view.setTextColor(TEXT);
        view.setTextSize(size);
        if (bold) view.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        view.setPadding(0,dp(4),0,dp(4));
        return view;
    }

    private EditText edit(String hint, boolean password) {
        EditText view = new EditText(this);
        view.setSingleLine(true);
        view.setHint(hint);
        view.setTextSize(16);
        view.setTextColor(TEXT);
        view.setHintTextColor(SOFT);
        if (password) view.setInputType(129);
        else view.setInputType(1);
        view.setPadding(dp(14),dp(12),dp(14),dp(12));
        view.setBackground(shape(CANVAS,12));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(-1,dp(53));
        params.bottomMargin=dp(12);
        view.setLayoutParams(params);
        return view;
    }

    private Button button(String label, boolean filled) {
        Button view = new Button(this);
        view.setText(label);
        view.setAllCaps(false);
        view.setTextSize(14);
        view.setTextColor(filled ? Color.WHITE : TEXT);
        view.setBackground(shape(filled ? ACCENT : CANVAS,13));
        view.setMinimumHeight(dp(49));
        return view;
    }

    private LinearLayout card(int padding) {
        LinearLayout surface = column();
        surface.setBackground(shape(SURFACE,20));
        surface.setPadding(dp(padding),dp(padding),dp(padding),dp(padding));
        surface.setElevation(dp(2));
        return surface;
    }

    private void screen(String heading, String subtitle) {
        LinearLayout root=column();
        root.setBackgroundColor(CANVAS);
        root.setPadding(dp(20),dp(28),dp(20),dp(14));
        root.setFitsSystemWindows(true);
        TextView product=text("GOREECLOUD  /  CALENDAR",12,true);
        product.setTextColor(ACCENT);
        root.addView(product);
        TextView h1=text(heading,29,true);
        LinearLayout.LayoutParams headingParams=new LinearLayout.LayoutParams(-1,-2);
        headingParams.topMargin=dp(16);
        root.addView(h1,headingParams);
        TextView sub=text(subtitle,14,false);
        sub.setTextColor(SOFT);
        root.addView(sub);
        status=text("",13,false);
        status.setTextColor(ACCENT);
        LinearLayout.LayoutParams statusParams=new LinearLayout.LayoutParams(-1,-2);
        statusParams.topMargin=dp(10);
        root.addView(status,statusParams);
        ScrollView scroll=new ScrollView(this);
        scroll.setFillViewport(true);
        body=column();
        body.setPadding(0,dp(12),0,dp(18));
        scroll.addView(body);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        rootLayout=root;
        setContentView(root);
    }

    private void renderLogin() {
        screen("Make room for what matters.","Sign in to your private self-hosted calendar.");
        LinearLayout form=card(20);
        form.addView(text("Calendar server",14,true));
        EditText server=edit("https://calendar.example.org",false);
        form.addView(server);
        form.addView(text("Email address",14,true));
        EditText email=edit("you@example.org",false);
        form.addView(email);
        form.addView(text("Password",14,true));
        EditText password=edit("Your password",true);
        form.addView(password);
        Button signIn=button("Sign in",true);
        form.addView(signIn);
        body.addView(form);
        TextView note=text("Create accounts from your server's local terminal. HTTPS is required.",13,false);
        note.setTextColor(SOFT);
        note.setPadding(0,dp(18),0,0);
        body.addView(note);
        signIn.setOnClickListener(v -> {
            String input=server.getText().toString().trim();
            Uri uri=Uri.parse(input);
            if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost()==null ||
                 uri.getUserInfo()!=null || uri.getQuery()!=null || uri.getFragment()!=null ||
                 (uri.getPath()!=null && !uri.getPath().isEmpty() && !uri.getPath().equals("/"))) {
                status.setText("Enter a valid HTTPS server origin without a path or login details.");
                return;
            }
            origin=input.endsWith("/") ? input.substring(0,input.length()-1) : input;
            String identity=email.getText().toString().trim();
            String secret=password.getText().toString();
            status.setText("Connecting securely…");
            perform(() -> {
                JSONObject payload=new JSONObject();
                payload.put("email",identity);
                payload.put("password",secret);
                return request("POST","/login",payload,null);
            },result -> {
                sessionToken=result.getString("token");
                password.setText("");
                renderDashboard();
            });
        });
    }

    private interface Work { JSONObject call() throws Exception; }
    private interface Done { void accept(JSONObject data) throws Exception; }

    private void perform(Work work, Done onSuccess) {
        worker.execute(() -> {
            try {
                JSONObject answer=work.call();
                runOnUiThread(() -> {
                    try {onSuccess.accept(answer);}
                    catch(Exception error) {showError(error.getMessage());}
                });
            } catch(Exception error) {
                runOnUiThread(() -> showError(error.getMessage()));
            }
        });
    }

    private void showError(String message) {
        if (status!=null) status.setText(message==null ? "Request failed" : message);
    }

    private JSONObject request(String method, String path, JSONObject data, String token) throws Exception {
        URL url=new URL(origin+"/api/v1"+path);
        HttpURLConnection connection=(HttpURLConnection)url.openConnection();
        connection.setInstanceFollowRedirects(false);
        connection.setConnectTimeout(10000);
        connection.setReadTimeout(10000);
        connection.setRequestMethod(method);
        connection.setRequestProperty("Accept","application/json");
        if(token!=null)connection.setRequestProperty("Authorization","Bearer "+token);
        if(data!=null) {
            connection.setRequestProperty("Content-Type","application/json");
            connection.setDoOutput(true);
            byte[] bytes=data.toString().getBytes(StandardCharsets.UTF_8);
            try(OutputStream output=connection.getOutputStream()){output.write(bytes);}
        }
        int code=connection.getResponseCode();
        InputStream stream=code<400?connection.getInputStream():connection.getErrorStream();
        if(stream==null)throw new Exception("Server returned no response");
        ByteArrayOutputStream buffer=new ByteArrayOutputStream();
        byte[] temp=new byte[4096];
        int n;int size=0;
        try(InputStream input=stream) {
            while((n=input.read(temp))!=-1) {
                size+=n;
                if(size>1024*1024)throw new Exception("Server response is too large");
                buffer.write(temp,0,n);
            }
        } finally {connection.disconnect();}
        JSONObject answer=new JSONObject(buffer.toString("UTF-8"));
        if(code<200 || code>=300)
            throw new Exception(answer.optString("error","Request failed ("+code+")"));
        return answer;
    }

    private void renderDashboard() {
        screen("Your schedule",selectedDate.format(DateTimeFormatter.ofPattern("EEEE, MMMM d")));
        LinearLayout controls=row();
        Button date=button("Choose date",false);
        date.setOnClickListener(v -> {
            DatePickerDialog picker=new DatePickerDialog(this,(view,year,month,day)->{
                selectedDate=LocalDate.of(year,month+1,day);
                renderDashboard();
            },selectedDate.getYear(),selectedDate.getMonthValue()-1,selectedDate.getDayOfMonth());
            picker.show();
        });
        controls.addView(date,new LinearLayout.LayoutParams(0,dp(52),1));
        Button refresh=button("Refresh",false);
        LinearLayout.LayoutParams refreshParams=new LinearLayout.LayoutParams(0,dp(52),1);
        refreshParams.leftMargin=dp(12);
        controls.addView(refresh,refreshParams);
        refresh.setOnClickListener(v -> loadAgenda());
        body.addView(controls);
        LinearLayout.LayoutParams spacer=new LinearLayout.LayoutParams(-1,dp(16));
        body.addView(new View(this),spacer);
        LinearLayout navigation=row();
        navigation.setBackground(shape(SURFACE,20));
        navigation.setPadding(dp(7),dp(7),dp(7),dp(7));
        Button agenda=button("Agenda",activeTab.equals("agenda"));
        Button tasks=button("Tasks",activeTab.equals("tasks"));
        Button add=button("＋ New",true);
        for(Button b:new Button[]{agenda,tasks,add}) {
            LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(0,dp(48),1);
            params.leftMargin=dp(3);
            navigation.addView(b,params);
        }
        agenda.setOnClickListener(v->{activeTab="agenda";renderDashboard();loadAgenda();});
        tasks.setOnClickListener(v->{activeTab="tasks";renderDashboard();loadTasks();});
        add.setOnClickListener(v->{if(activeTab.equals("tasks"))newTask();else newEvent();});
        resultContainer=column();
        body.addView(resultContainer);
        LinearLayout.LayoutParams dockParams=new LinearLayout.LayoutParams(-1,dp(62));
        dockParams.leftMargin=dp(14);
        dockParams.rightMargin=dp(14);
        dockParams.bottomMargin=dp(14);
        rootLayout.addView(navigation,dockParams);
        Button logout=button("Sign out",false);
        LinearLayout.LayoutParams signoutParams=new LinearLayout.LayoutParams(-1,dp(50));
        signoutParams.topMargin=dp(16);
        body.addView(logout,signoutParams);
        logout.setOnClickListener(v->{
            String old=sessionToken;
            sessionToken=null;
            selectedCalendarId=null;
            renderLogin();
            if(old!=null)perform(() -> request("POST","/logout",null,old),answer->{});
        });
        if(activeTab.equals("agenda")) loadAgenda(); else loadTasks();
    }

    private String queryDate(LocalDate d) {
        return d.atStartOfDay(ZoneId.systemDefault()).toOffsetDateTime().toString();
    }

    private void loadAgenda() {
        if(sessionToken==null)return;
        status.setText("Loading your calendar…");
        final String token=sessionToken;
        final LocalDate requestedDay=selectedDate;
        perform(() -> {
            JSONArray calendars=request("GET","/calendars",null,token).getJSONArray("calendars");
            if(calendars.length()>0 && selectedCalendarId==null)
                selectedCalendarId=calendars.getJSONObject(0).getString("id");
            String start=URLEncoder.encode(queryDate(selectedDate),"UTF-8");
            String end=URLEncoder.encode(queryDate(selectedDate.plusDays(1)),"UTF-8");
            JSONObject events=request("GET","/events?start="+start+"&end="+end,null,token);
            return new JSONObject().put("events",events.getJSONArray("events"));
        },result->{
            if(!activeTab.equals("agenda") || !token.equals(sessionToken) || !requestedDay.equals(selectedDate))return;
            status.setText("");
            resultContainer.removeAllViews();
            JSONArray events=result.getJSONArray("events");
            LinearLayout list=card(16);
            list.addView(text("Events on "+selectedDate.format(DateTimeFormatter.ofPattern("MMM d")),19,true));
            if(events.length()==0)list.addView(text("Nothing planned. Enjoy the space.",14,false));
            for(int i=0;i<events.length();i++) {
                JSONObject event=events.getJSONObject(i);
                LocalDateTime local=java.time.OffsetDateTime.parse(event.getString("start_at"))
                    .atZoneSameInstant(ZoneId.systemDefault()).toLocalDateTime();
                TextView item=text(local.format(DateTimeFormatter.ofPattern("h:mm a"))+
                    "  •  "+event.getString("title"),16,true);
                item.setBackground(shape(CANVAS,12));
                item.setPadding(dp(13),dp(14),dp(13),dp(14));
                LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,-2);
                params.topMargin=dp(9);
                list.addView(item,params);
            }
            resultContainer.addView(list);
        });
    }

    private void loadTasks() {
        if(sessionToken==null)return;
        status.setText("Loading tasks…");
        final String token=sessionToken;
        perform(() -> request("GET","/tasks",null,token),result->{
            if(!activeTab.equals("tasks")||!token.equals(sessionToken))return;
            status.setText("");
            resultContainer.removeAllViews();
            JSONArray tasks=result.getJSONArray("tasks");
            LinearLayout list=card(16);
            list.addView(text("Tasks",19,true));
            if(tasks.length()==0)list.addView(text("All caught up.",14,false));
            for(int i=0;i<tasks.length();i++) {
                JSONObject task=tasks.getJSONObject(i);
                String name=task.getString("title");
                boolean done=task.getInt("done")!=0;
                Button taskButton=button((done?"✓  ":"○  ")+name,false);
                LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,dp(52));
                params.topMargin=dp(8);
                list.addView(taskButton,params);
                String id=task.getString("id");
                taskButton.setOnClickListener(v->perform(()->
                    request("PATCH","/tasks/"+id,new JSONObject().put("done",!done),token),
                    answer->{renderDashboard();}));
            }
            resultContainer.addView(list);
        });
    }

    private void newTask() {
        if(selectedCalendarId==null){showError("No calendar is available.");return;}
        EditText field=edit("New task",false);
        new AlertDialog.Builder(this).setTitle("New task").setView(field)
            .setNegativeButton("Cancel",null)
            .setPositiveButton("Create",(dialog,which)->{
                String name=field.getText().toString().trim();
                if(name.isEmpty())return;
                perform(() -> request("POST","/tasks",new JSONObject()
                    .put("title",name).put("calendar_id",selectedCalendarId),sessionToken),
                    answer->{renderDashboard();});
            }).show();
    }

    private void newEvent() {
        if(selectedCalendarId==null){showError("No calendar is available.");return;}
        EditText field=edit("Event title",false);
        new AlertDialog.Builder(this).setTitle("New event • "+selectedDate)
            .setMessage("Creates a one-hour event at 9:00 AM (local time).")
            .setView(field).setNegativeButton("Cancel",null)
            .setPositiveButton("Create",(dialog,which)->{
                String title=field.getText().toString().trim();
                if(title.isEmpty())return;
                ZonedDateTime begin=selectedDate.atTime(9,0).atZone(ZoneId.systemDefault());
                ZonedDateTime finish=begin.plusHours(1);
                perform(() -> request("POST","/events",new JSONObject()
                    .put("calendar_id",selectedCalendarId).put("title",title)
                    .put("start_at",begin.toOffsetDateTime().toString())
                    .put("end_at",finish.toOffsetDateTime().toString()),sessionToken),
                    answer->{renderDashboard();});
            }).show();
    }
}
