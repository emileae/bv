
/* =============== MASONRY ========================= */

var window_width = $("#goal_container_front").width();

//var window_height = $(window).height();
//$(".reveal-modal").css("height", window_height*0.75);
var num_columns = Math.floor(window_width / 240);// 240 == width in pixels of .item
var column_width = window_width / num_columns;
var $container = $('#goal_list');

$container.imagesLoaded( function() {
    $container.masonry({
      itemSelector: '.item',
      "gutter": 10,
      "isFitWidth": true,
      columnWidth: ".item"//function( containerWidth ) {
    });
    
});

function reload_masonry_container($container){
    $container.imagesLoaded( function() {

    $container.masonry({
      itemSelector: '.item',
      "gutter": 10,
      "isFitWidth": true,
      columnWidth: ".item"//function( containerWidth ) {
    });
    
});
};

/* =============== MASONRY ========================= */


/* =============== UTILITY ========================= */
$("body").on("transitionend webkitTransitionEnd oTransitionEnd otransitionend MSTransitionEnd", ".success", function(){
    $(this).removeClass("success");
});

$(document).on("scroll", function(){
    var document_height = $(document).outerHeight();
    var window_height = $(window).outerHeight();
    var scroll_pos = $(document).scrollTop();
    
    var loading_content = false;
    
    if( (scroll_pos + window_height) > ( document_height * 0.8 ) && !loading_content ){
        loading_content = true;

        if( $("#goal_list").length ){
            load_more_goals();
        }else if( $("#feed_container_column").length ){
            load_more_feed_goals();
        };
    };
    
    if( $("#bv_feed_banner") ){
        if( $(".sticky").length ){
            var eTop = $(".sticky").offset().top;
            var rel_pos = eTop - $(window).scrollTop();
            if( rel_pos <= 0 ){
                $("#bv_feed_banner").remove();
                $(".sticky").css("top", "0px");
                $(".sticky").addClass("fixed");
                $(".fixed").removeClass("sticky");
                $("body").css("margin-top", "47px");
            }
        };
    };
    
});

$(document).on('close', '#userModal', function () {
  $("#user_profile_container").html("<p>Loading</p>");
});

$("body").on("click", "#login_btn_toggle", function(){
    $("#site_description").css("left", "0%");
    $("#login_btn_toggle").hide();
    $("#signup_btn_toggle").show();
});
$("body").on("click", "#signup_btn_toggle", function(){
    $("#site_description").css("left", "-200%");
    $("#signup_btn_toggle").hide();
    $("#login_btn_toggle").show();
});

$("body").on("click", "#login_toggle", function(){
    $("#bv_description").addClass("hidden");
    $("#register").addClass("hidden");
    $("#login").removeClass("hidden");
});
$("body").on("click", "#register_toggle", function(){
    $("#bv_description").addClass("hidden");
    $("#login").addClass("hidden");
    $("#register").removeClass("hidden");
});

$("body").on("click", "#bv_logo", function(){
    $("#site_description").css("left", "-100%");
});

// dotdotdot and orient feed image
$(window).on("load", function(){
    ellipsis();
    resize_feed_image();
    size_profile_img_container();
});
/*
$(window).on("load", function(){
    resize_feed_image();
});
*/

function ellipsis(){
    console.log("ellipsis");
    if( $(".goal_text_description").length ){
        $(".goal_text_description").dotdotdot();
    };
};

/* =============== UTILITY ========================= */


/* ================== CLICK EVENTS =================== */

$('body').on('click', '.media_modal', function(){
    var $this = $(this);
    var img_url = $this.data("img-url");
    var youtube_id = $this.data("youtube-id");
    if( youtube_id == "no" ){
        youtube_id = false
    };
    $('#mediaModal').foundation('reveal', 'open');
    
    if( youtube_id ){
        $("#modal_media_container").html('<iframe id="vid_iframe" type="text/html" width="640" height="390" src="http://www.youtube.com/embed/'+youtube_id+'?autoplay=1" frameborder="0"/>');
    }else{
        $("#modal_media_container").html("<img class='' src='"+img_url+"' />");
    };
    
});

$('body').on('click', '.album_icon', function(e){
    e.stopPropagation();
});

$('body').on('click', '.share_point', function(){
    add_user_share_point();
});

$('body').on( "click", ".goal_like_btn", function(e) {
    e.stopPropagation();
});
$('body').on( "click", ".user_controls", function(e) {
    e.stopPropagation();
});
$('body').on( "click", ".user_profile_modal", function(e) {
    e.stopPropagation();
});

$('body').on("click", '.user_profile_modal', function(){
    $('#userModal').foundation('reveal', 'open');
    var id = $(this).data("user-id");
    var user_html = show_user_profile(id);
});
$(document).on('close', '#userModal', function () {
    $("#user_profile_container").html("<p>Loading</p>");
});

$("body").on("click", ".goal_modal_trigger", function(){
    $('#feedModal').foundation('reveal', 'open');
    var id = $(this).data("goal-id");
    var goal_html = show_goal_profile(id);
    add_view(id);
});

$(document).on('close', '#feedModal', function () {
    $("#goal_profile_container").html("<p>Loading</p>");
});


$("body").on('click', '.goal_like_btn', function(){
    var id = $(this).data("goal-id");
    add_like(id);
});

$("body").on("click", ".steal_goal", function(e){
    var $this = $(this);
    var goal_id = $this.data("goal-id");
    var victim_name = $this.data("user-name");
    
    $("#victim_goal_name").html(victim_name);
    $("#steal_goal").val(goal_id);
    
    $('#stealModal').foundation('reveal', 'open');
    e.stopPropogation();
});
$("body").on("click", ".steal_victory", function(e){
    var $this = $(this);
    var goal_id = $this.data("goal-id");
    var victim_name = $this.data("user-name");
    
    $("#victim_victory_name").html(victim_name);
    $("#steal_victory").val(goal_id);
    
    $('#stealVictoryModal').foundation('reveal', 'open');
    e.stopPropogation();
});

$("body").on('click', '.achieved_btn', function(){
    var id = $(this).data("goal-id");
    make_victory(id);
});
$("body").on("click", '.follow_user', function(){
    var id = $(this).data("user-id");
    //alert(id);
    follow(id);
})
$("body").on("click", '.unfollow_user', function(){
    var id = $(this).data("user-id");
    unfollow(id);
});

$("body").on("click", "#title_description_edit_btn", function(){
    $("#set_title_description").addClass("hidden");
    $("#title_description_edit_form_container").removeClass("hidden");
});

$("body").on("click", ".make_cover_img", function(){
    var $this = $(this);
    var img_url = $this.data("img-url");
    var goal_id = $this.data("goal-id");
    var loop_index = $this.data("loop-index");
    make_cover_img(img_url, goal_id, loop_index);
});

$("body").on("click", ".delete_media", function(){
    var $this = $(this);
    var img_url = $this.data("img-url");
    var goal_id = $this.data("goal-id");
    var loop_index = $this.data("loop-index");

    delete_media(img_url, goal_id, loop_index);
});

$("body").on("click", ".goal_delete", function(){
    var goal_id = $(this).data("goal-id");
    delete_goal(goal_id);
});

$("body").on("click", "#change_profile_img", function(e){
    e.preventDefault();
    $(this).addClass("hidden");
    $("#profile_img_form").removeClass("hidden");
});

$('body').on('click', '#share_btn', function(){
    var $this = $(this);
    if( $this.hasClass("toggle_on") ){
        $(".share_container").removeClass("hidden");
        $(".edit_container").addClass("hidden");
    }else{
        $(".share_container").addClass("hidden");
    }
});
$('body').on('click', '#change_btn', function(){
    var $this = $(this);
    if( $this.hasClass("toggle_on") ){
        $(".edit_container").removeClass("hidden");
        $(".share_container").addClass("hidden");
    }else{
        $(".edit_container").addClass("hidden");
    }
});

$("body").on("click", ".toggle_on", function(){
    var $this = $(this);
    $( "#toggle_container" ).css("max-height", "1000px");
    $(".toggle_on").addClass("toggle_off");
    $(".toggle_off").removeClass("toggle_on");
});
$("body").on("click", ".toggle_off", function(){
    var $this = $(this);
    $( "#toggle_container" ).css("max-height", "0px");
    $(".toggle_off").addClass("toggle_on");
    $(".toggle_on").removeClass("toggle_off");
});


$("body").on("click", ".goal_form_toggle_on", function(){
    $( "#goal_add_form_container" ).css("max-height", "1000px");
    $( "#goal_form_toggle" ).removeClass("goal_form_toggle_on");
    $( "#goal_form_toggle" ).addClass("goal_form_toggle_off");
    $("#goal_form_toggle").removeClass("icon-plus");
    $("#goal_form_toggle").addClass("icon-minus");
});
$("body").on("click", ".goal_form_toggle_off", function(){
    $( "#goal_add_form_container" ).css("max-height", "0px");
    $( "#goal_form_toggle" ).removeClass("goal_form_toggle_off");
    $( "#goal_form_toggle" ).addClass("goal_form_toggle_on");
    $("#goal_form_toggle").removeClass("icon-minus");
    $("#goal_form_toggle").addClass("icon-plus");
});

$("body").on("click", ".vision_view_toggle_on", function(){
    toggle_vision_to_list();
});
function toggle_vision_to_list(){
    var w_w = $(window).width();
    $(".item").css("width", w_w);
    $(".item").addClass("list_view");
    
    $(".goal_card_img").addClass("float_left");
    $(".goal_card_img").css("position", "absolute");
    $(".goal_card_img").css("top", "0px");
    $(".goal_card_img").css("bottom", "0px");
    $(".goal_card_img").css("margin", "auto");
    
    $(".goal_card_text").addClass("float_left");
    
    $(".bottom_band").addClass("hidden");
    $(".achieved_icon_container").addClass("hidden");//achieved_icon_container
    $(".goal_description").addClass("hidden");//goal_description
    $(".view_like_container_goal").addClass("hidden");//view_like_container_goal
    $(".user_controls").addClass("hidden");//user_controls
    $(".goal_card_title").css("margin-left", "80px");
    
    $("#goal_list").addClass("goal_list_listview");
    $(".goal_description").removeClass("overflow_ellipsis");
    $(".view_like_container_goal").addClass("text_left");
    $(".goal_description").dotdotdot();
    reload_masonry_container($("#goal_list"));
    $("#vision_view_toggle").removeClass("vision_view_toggle_on");
    $("#vision_view_toggle").addClass("vision_view_toggle_off");
    $("#vision_view_toggle").removeClass("icon-list");
    $("#vision_view_toggle").addClass("icon-table");
};

$("body").on("click", ".vision_view_toggle_off", function(){
    toggle_vision_to_masonry();
});
function toggle_vision_to_masonry(){
    $(".item").css("width", "385px");
    $(".item").removeClass("list_view");
    
    $(".goal_card_img").removeClass("float_left");
    $(".goal_card_img").css("position", "relative");
    $(".goal_card_img").css("top", "0px");
    $(".goal_card_img").css("bottom", "0px");
    $(".goal_card_img").css("margin", "auto");
    
    $(".goal_card_text").removeClass("float_left");
    
    $(".bottom_band").removeClass("hidden");
    $(".achieved_icon_container").removeClass("hidden");//achieved_icon_container
    $(".goal_description").removeClass("hidden");//goal_description
    $(".view_like_container_goal").removeClass("hidden");//view_like_container_goal
    //$(".user_controls").removeClass("hidden");//user_controls
    $(".goal_card_title").css("margin-left", "0px");
    
    $("#goal_list").removeClass("goal_list_listview");
    $(".goal_description").addClass("overflow_ellipsis");
    $(".view_like_container_goal").removeClass("text_left");
    reload_masonry_container($("#goal_list"));
    $("#vision_view_toggle").removeClass("vision_view_toggle_off");
    $("#vision_view_toggle").addClass("vision_view_toggle_on");
    $("#vision_view_toggle").removeClass("icon-table");
    $("#vision_view_toggle").addClass("icon-list");
};

$("body").on("click", ".victory_view_toggle_on", function(){
    toggle_victory_to_list();
});
function toggle_victory_to_list(){
    var w_w = $(window).width();
    $(".item").css("width", w_w);
    $(".item").addClass("list_view");
    
    $(".goal_card_img").addClass("float_left");
    $(".goal_card_img").css("position", "absolute");
    $(".goal_card_img").css("top", "0px");
    $(".goal_card_img").css("bottom", "0px");
    $(".goal_card_img").css("margin", "auto");
    
    $(".goal_card_text").addClass("float_left");
    $(".goal_card_title").css("margin-left", "80px");
    
    $(".bottom_band").addClass("hidden");
    $(".achieved_icon_container").addClass("hidden");//achieved_icon_container
    $(".goal_description").addClass("hidden");//goal_description
    $(".view_like_container_goal").addClass("hidden");//view_like_container_goal
    $(".user_controls").addClass("hidden");//user_controls
    
    $("#goal_list").addClass("goal_list_listview");
    $(".goal_description").removeClass("overflow_ellipsis");
    $(".view_like_container_goal").addClass("text_left");
    $(".goal_description").dotdotdot();
    
    reload_masonry_container($("#goal_list"));
    $( "#victory_view_toggle" ).removeClass("victory_view_toggle_on");
    $( "#victory_view_toggle" ).addClass("victory_view_toggle_off");
    $("#victory_view_toggle").removeClass("icon-list");
    $("#victory_view_toggle").addClass("icon-table");
};
$("body").on("click", ".victory_view_toggle_off", function(){
    toggle_victory_to_masonry();
});
function toggle_victory_to_masonry(){
    $(".item").css("width", "385px");
    $(".item").removeClass("list_view");
    
    $(".goal_card_img").removeClass("float_left");
    $(".goal_card_img").css("position", "relative");
    $(".goal_card_img").css("top", "0px");
    $(".goal_card_img").css("bottom", "0px");
    $(".goal_card_img").css("margin", "auto");
    
    $(".goal_card_text").removeClass("float_left");
    $(".goal_card_title").css("margin-left", "0px");
    
    $(".bottom_band").removeClass("hidden");
    $("#goal_list").removeClass("goal_list_listview");
    $(".goal_description").addClass("overflow_ellipsis");
    $(".view_like_container_goal").removeClass("text_left");
    
    reload_masonry_container($("#goal_list"));
    $( "#victory_view_toggle" ).removeClass("victory_view_toggle_off");
    $( "#victory_view_toggle" ).addClass("victory_view_toggle_on");
    $("#victory_view_toggle").removeClass("icon-table");
    $("#victory_view_toggle").addClass("icon-list");
};

$("body").on("click", ".vic_orbit_thumb_pic", function(){
    var $main_img = $("#modal_goal_profile_img")
    var main_img = $main_img.attr("src");
    var $iframe = $("#vid_iframe");
    $iframe.attr("src", "")
    $iframe.addClass("hidden");

    var img_url = $(this).data("img-url");
    
     $(".feed_cover_container").css("background-color", "transparent");

    $main_img.attr("src", img_url);
    
    resize_feed_image();
    
});
$("body").on("click", ".vic_orbit_thumb_vid", function(){
    var $main_img = $("#modal_goal_profile_img");
    var $iframe = $("#vid_iframe");
    //http://www.youtube.com/embed/M7lc1UVf-VE?autoplay=1&origin=http://example.com
    $iframe.removeClass("hidden");
    $main_img.addClass("hidden");
    
    $(".feed_cover_container").css("background-image", "none");
    $(".feed_cover_container").css("background-color", "white");
    
    /*var container_width = $(".feed_cover_container").width();
    var iframe_width = $iframe.width();
    var difference = Number(container_width) - Number(iframe_width);
    var margin = difference / 2;
    
    $iframe.css("margin-left", margin+"px");*/
    
    /*var container_height = $(".feed_cover_container").height();
    var iframe_height = $iframe.height();
    var difference_h = Number(container_width) - Number(iframe_width);
    var margin_t = difference_h / 2;
    
    $iframe.css("margin-top", margin_t+"px");*/
    
    $main_img.attr("src", "");
    var video_id = $(this).data("img-url");
    
    $iframe.attr("src", "http://www.youtube.com/embed/"+video_id+"?autoplay=1");
    /*
        http://img.youtube.com/vi/<insert-youtube-video-id-here>/default.jpg
        hqdefault.jpg
        mqdefault.jpg
        sddefault.jpg
        maxresdefault.jpg
        
        http://avexdesigns.com/responsive-youtube-embed/
        
    */
});

/* ================== CLICK EVENTS =================== */

/* ================== Jquery UI ======================== */
/*
$("body").on("click", ".feed_image_edit", function(){
    $("#reposition_instructions").html("Now drag image");
    listen_for_drag_feed_img();
});
*/
$("body").on("click", "#reposition_instructions", function(){
    $("#reposition_instructions").html("Now drag image");
    listen_for_drag_feed_img();
});

/*
$("body").on("click", "#profile_img_container", function(){
    $("#reposition_instructions").html("Now drag image");
    listen_for_drag_feed_img($("#profile_image_edit"), $(".profile_img_container"));
});
*/

function listen_for_drag_feed_img(){
    $(".feed_image_edit").draggable({ axis: "y" });

    $( ".feed_image_container_edit" ).droppable({
      drop: function( event, ui ) {
        var top_pos = ui.position.top;
        $("#top").val(top_pos);
        $("#reposition_instructions").addClass("hidden");
        $("#image_crop_form").removeClass("hidden");
      }
    });
    
    /*$( ".resizable" ).resizable({
      aspectRatio: true
    });*/
    
};

/* ================== Jquery UI ======================== */

/* ====================== FORM SUBMITS ========================= */

$("body").on("click", "#user_search_submit", function(){
    var user_email = $("#user_email").val();
    if( user_email.length > 0 ){
        user_search(user_email);
    };
});
$("body").on("submit", "#user_search_form", function(e){
    e.preventDefault();
    var user_email = $("#user_email").val();
    if( user_email.length > 0 ){
        user_search(user_email);
    };
});


$("body").on("submit", "#forgot_password_form", function(e){
    e.preventDefault();
    var email = $("#recovery_email").val();
    submit_forgotten_pw(email);
});

$("body").on("submit", "#change_pw_form", function(e){
    e.preventDefault();
    var old_password = $("#old_password").val();
    var new_password = $("#new_password").val();
    var repeat_password = $("#repeat_password").val();
    
    change_password(old_password, new_password, repeat_password);
});

$("body").on("submit", "#change_email_form", function(e){
    e.preventDefault();
    var password = $("#password").val();
    var old_email = $("#old_email").val();
    var new_email = $("#new_email").val();
    
    change_email(password, old_email, new_email);
});

$("body").on("click", "#delete_account", function(){
    $('#deleteAccountModal').foundation('reveal', 'open');
});
$("body").on("click", "#delete_acc", function(){
    delete_account();
});
$("body").on("click", "#delete_abort", function(){
    $('#deleteAccountModal').foundation('reveal', 'close');
});

$("body").on("click", "#profile_settings_submit", function(e){
    e.preventDefault();
    if( verify_profile_settings() ){
        submit_profile_settings();
    };
});

$("body").on("click", "#image_top_submit", function(e){
    e.preventDefault();
    submit_image_position();
});

$("body").on("click", "#title_description_submit", function(e){
    e.preventDefault();
    //alert("submit_title_description_edit");
    submit_title_description_edit();
});

$("body").on("click", "#profile_img_submit", function(){
    var user_id = $("#user_id").val();
    if( check_file_size($("#user_profile_img"), 600000) ){
        $.when(get_upload_url("/upload_profile_img/"+user_id, "profile")).then(function(data){
            $("#profile_img_form").attr("action", data);
            $("#profile_img_form").trigger("submit");
        });
    };
});

// form verification verify
$("body").on("submit", "#goal_submit_form", function(e){
    if( !$("#goal_img_url").val() ){
        e.preventDefault();
        alert("Please include an image URL");
    };
});
$("body").on("submit", "#vic_img_url_form", function(e){
    if( !$("#vic_img_url").val() ){
        e.preventDefault();
        alert("Please include an image URL");
    };
});
$("body").on("submit", "#goal_submit_video_embed_form", function(e){
    if( !$("#goal_video_embed").val() ){
        e.preventDefault();
        alert("Please include a youtube URL");
    };
});

//goal_submit_video_embed_form

$("body").on("click", "#goal_img_submit", function(){
    if( !$("#goal_img").val() ){
        alert("Please select a file");
    }else{
        var user_id = $("#user_id").val();
        var already_achieved = $("#already_achieved").val();
        if( already_achieved ){
            var victory = "yes"
        }else{
            var victory = "no"
        };
        
        if( $("#edit_goal_id").length > 0 ){
            var edit_goal_id = $("#edit_goal_id").val();
        }else{
            var edit_goal_id = "";
        };
        
        if( edit_goal_id.length ){
            if( check_file_size($("#goal_img"), 3000000) ){
                $.when(get_upload_url("/upload_goal_edit_img/"+user_id+"/"+edit_goal_id, "goal")).then(function(data){
                    $("#goal_img_upload_form").attr("action", data);
                    $("#goal_img_upload_form").trigger("submit");
                });
            };
        }else{
            if( check_file_size($("#goal_img"), 3000000) ){
                $.when( add_goal_ajax() ).then(function(goal_id){
                    $.when(get_upload_url("/upload_goal_img/"+user_id+"/"+goal_id+"/"+victory, "goal")).then(function(data){
                        $("#goal_img_upload_form").attr("action", data);
                        $("#goal_img_upload_form").trigger("submit");
                    });
                });
            }
        };
    };
});

$("body").on("click", "#vic_img_url_submit", function(e){
    e.preventDefault();
    var img_url = $("#vic_img_url").val();
    var goal_id = $("#vic_img_url_goal_id").val();
    if (img_url.length > 0){
        submit_vic_img_url_form(img_url, goal_id);
    }
    //"#vic_img_url_form"
});

$("body").on("click", "#victory_img_submit", function(){
    var user_id = $("#user_id").val();
    var goal_id = $("#goal_id").val();
    if( !goal_id ){
        var goal_id = $("#vic_congrats_goal_id").val();
    };
    if( check_file_size($("#vic_img"), 3000000) ){
        //$.when( add_goal_ajax() ).then(function(goal_id){
            $.when(get_upload_url("/upload_vic_img/"+user_id+"/"+goal_id, "vic_pic")).then(function(data){
                $("#victory_img_upload_form").attr("action", data);
                $("#victory_img_upload_form").trigger("submit");
            });
        //});
    };
});

/* ====================== FORM SUBMITS ========================= */


/* ============= UTILITY FUNCTIONS & AJAX ============================ */

function add_user_share_point(){
    $.ajax({
        type: "post",
        url: '/share_point',
        success: success
    }).fail(function(e){
        alert("error - share_point");
    });

    function success(data){
    };
};

function user_search(user_email){
    $.ajax({
        type: "get",
        data: {"user_email": user_email},
        url: '/search_users',
        success: success
    }).fail(function(e){
        alert("error - user_search");
    });

    function success(data){
        $("#search_results").removeClass("hidden");
        $("#search_results").children("ul").html("");
        var html = "";
        for( var i=0; i<data["users"].length; i++ ){
            html += "<li class='user_profile_modal pointer' data-user-id='"+data['users'][i]['id']+"'>"+data['users'][i]['name']+"</li>"
        };
        $("#search_results").children("ul").append(html);
        //alert(JSON.stringify(data));
    };
};

function delete_account(){
     NProgress.start();
    $.ajax({
        type: "post",
        url: '/delete_account',
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - delete_account");
    });

    function success(data){
         NProgress.done();
        alert("Deleted");
    };
};

function change_password(old_password, new_password, repeat_password){
     NProgress.start();
    $.ajax({
        type: "post",
        url: '/change_password',
        data: {"old_password": old_password, "new_password": new_password, "repeat_password": repeat_password},
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - change_password");
    });

    function success(data){
         NProgress.done();
        if( data["message"] == "success" ){
            $("#old_password").val("");
            $("#new_password").val("");
            $("#repeat_password").val("");
            $("#change_pw_message").html("Password Changed");
        }else{
            $("#old_password").val("");
            $("#new_password").val("");
            $("#repeat_password").val("");
            $("#change_pw_message").html(data["message"]);
        };
    };
};

function change_email(password, old_email, new_email){
     NProgress.start();
    $.ajax({
        type: "post",
        url: '/change_email',
        data: {"password": password, "old_email": old_email, "new_email": new_email},
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - change_email");
    });

    function success(data){
         NProgress.done();
        if( data["message"] == "success" ){
            $("#password").val("");
            $("#old_email").val("");
            $("#new_email").val("");
            $("#change_email_message").html("Email Changed");
        }else{
            $("#password").val("");
            $("#old_email").val("");
            $("#new_email").val("");
            $("#change_email_message").html(data["message"]);
        };
    };
};

function submit_forgotten_pw(email){
     NProgress.start();
    $.ajax({
        type: "post",
        url: '/forgot_password',
        data: {"recovery_email": email},
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - recovery_email");
    });

    function success(data){
         NProgress.done();
        alert(data["message"]);
    };
};

function size_profile_img_container(){
    var profile_column_width = $(".profile_img_container").css("width");
    $(".profile_img_container").css("height", profile_column_width);
};

function resize_feed_image(){
    $(".feed_image").each(function(i, obj){
        var img_id = $(this).attr("id");
        orient_feed_img(img_id);
    });
};

function orient_feed_img(img_id){
    
    var $this = $("#"+img_id);

    var aspect = $this.width() / $this.height();// w/h
    
    if(aspect > 2.18){
        $this.css("width", "100%");
        $this.css("height", "auto");
        $this.css("position", "absolute");
        $this.css("top", "0px");
        $this.css("bottom", "0px");
        $this.css("left", "0px");
        $this.css("right", "0px");
        $this.css("margin", "auto");
    }else if( aspect == 1 ){
        $this.css("height", "100%");
        $this.css("width", "auto");
        $this.css("margin", "auto");
    }else if( aspect < 2.18 ){
        $this.css("position", "absolute");
        $this.css("height", "100%");
        $this.css("width", "auto");
        $this.css("left", "0px");
        $this.css("right", "0px");
        $this.css("margin", "auto");
    };
};

function submit_vic_img_url_form(img_url, goal_id){
     NProgress.start();
    
    function success(data){
        var img_src = data["img_url"];
        
        var html = '<div class="item"><img src="'+img_src+'" class="goal_card_img" /><div class="goal_card_text" class="row text-center"><span class="button tiny">Make Cover Image</span></div></div>';
        
        $("#goal_list").prepend(html);
        
        $("#panel-img_url").addClass("success");
        var html_array = [];
        html_array.push(html);
        
        $("#goal_list").masonry.layout();
        
        //reload_masonry_container($("#goal_list"));
        
        $("#goal_list").append( html ).masonry( 'appended', html );
         NProgress.done();
    };
    
    $.ajax({
        type: "post",
        url: '/add_vic_img_url',
        data: {"vic_img_url": img_url, "vic_img_url_goal_id":goal_id},
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - submit_vic_img_url_form");
    });
};

function delete_goal(goal_id){
     NProgress.start();
     
    function success(data){
        $('#feedModal').foundation('reveal', 'close');
        //alert("goal_"+data["goal_id"]);
        //$("goal_"+data["goal_id"]).remove();
        var goal_id = data["goal_id"];
        
        //$("#goal_"+goal_id).css("display", "none");
        
        $('#goal_list').masonry( 'remove', $("#goal_"+goal_id) );
        $('#goal_list').masonry().layout();
         NProgress.done();
    };
     
    $.ajax({
        type: "post",
        url: '/delete_goal',
        data: {"goal_id": goal_id},
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - delete_goal");
    });
    
};

function make_cover_img(img_url, goal_id, loop_index){
     NProgress.start();
    
    function success(data){
        $(".feed_image").attr("src", data["img_url"]);
        $("#vic_pic_"+loop_index).attr("src", data["old_cover"]);
        $("#make_cover_"+loop_index).data( "img-url", data["old_cover"] );
         NProgress.done();
    };
    
    $.ajax({
        type: "post",
        url: '/make_cover',
        data: {"img_url": img_url, "goal_id": goal_id},
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - make_cover_img");
    });
};

function delete_media(img_url, goal_id, loop_index){
     NProgress.start();
    
    function success(data){
        $("#edit_goal_"+loop_index).remove();
        reload_masonry_layout();
        NProgress.done();
    };
    
    $.ajax({
        type: "post",
        url: '/delete_media',
        data: {"img_url": img_url, "goal_id": goal_id},
        success: success
    }).fail(function(e){
        alert("error - delete img");
         NProgress.done();
    });
};

function add_goal_ajax(){
    var dfd = new jQuery.Deferred();
    
    var goal_title = $("#goal_title_img_upload").val();
    var goal_description = $("#goal_description_img_upload").val();
    if($("#already_achieved")){
        var already_achieved = $("#already_achieved").val();
    }else{
        var already_achieved = "no";
    };
    
    NProgress.start();
    
    function success(data){
        var goal_id = data["goal_id"];
        //$("#goal_id").val(goal_id);
        NProgress.done();
        dfd.resolve(goal_id);
    };
    
    $.ajax({
        type: "POST",
        url: '/add_goal_ajax',
        data: {"goal_title": goal_title,
        "goal_description": goal_description,
        "already_achieved": already_achieved
        },
        success: success
    }).fail(function(e){
        alert("error - add_goal_ajax");
        NProgress.done();
        dfd.reject(data);
    });
    
    return dfd.promise();
    
};

function verify_profile_settings(){
    var user_name = $("#user_name").val();
    if( user_name.length < 0 ){
        $("#user_name").addClass("error");
        return false
    }else{
        return true
    };
};

function submit_profile_settings(){
     NProgress.start();
    var user_name = $("#user_name").val();
    var user_description = $("#user_description").val();
    
    function success(data){
         NProgress.done();
        $("#profile_settings_form").addClass("success");
    };
    
    $.ajax({
        type: "post",
        url: '/settings',
        data: {"user_name": user_name, "user_description": user_description},
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - submit_profile_settings");
    });
};

function submit_title_description_edit(){
     NProgress.start();
    var edit_url = $("#edit_url").val();
    var edit_title = $("#edit_title").val();
    var edit_description = $("#edit_description").val();
    var goal_id = $("#goal_id_td").val();
    
    function success(data){
        //$("#title_description_edit_form_container").addClass("hidden");
        //$("#set_title_description").removeClass("hidden");
        //$("#set_title").html(data["title"]);
        //$("#set_description").html(data["description"]);
        //alert(data["edit_url"]);
        $("#feed_image_"+data["goal_id"]).attr("src", data["edit_url"]);
        $("#image_edit").addClass("success");
        resize_feed_image();
         NProgress.done();
    };
    
    $.ajax({
        type: "post",
        url: '/edit_title_description',
        data: {"edit_title": edit_title, "goal_id": goal_id, "edit_description": edit_description, "edit_url": edit_url},
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - submit_title_description_edit");
    });
}

function submit_image_position(){
    var top_pos = $("#top").val();
    var goal_id = $("#goal_id").val();
    
    function success(data){
        $(".feed_image_edit").css("top", data["top"]+"px");
        $("#reposition_instructions").html("Reposition");
        $("#reposition_instructions").removeClass("hidden");
        $("#image_crop_form").addClass("hidden");
    };
    
    $.ajax({
        type: "post",
        url: '/save_img_pos',
        data: {"top": top_pos, "goal_id": goal_id},
        success: success
    }).fail(function(e){
        alert("error - submit_image_position");
    });
};

function show_user_profile(id){
     NProgress.start();
    
    function success(data){
         NProgress.done();
        $("#user_profile_container").html(data);
        size_profile_img_container();
        $(".goal_description").dotdotdot();
    };
    
    $.ajax({
        type: "get",
        url: '/get_user_profile/'+id,
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - get_user_html");
    });
};
function show_goal_profile(id){
     NProgress.start();
    
    function success(data){
         NProgress.done();
        $("#goal_profile_container").html(data);
        size_profile_img_container();
        $(".goal_page_description").dotdotdot();
    };
    
    $.ajax({
        type: "get",
        url: '/get_goal_profile/'+id,
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - get_user_html");
    });
};

function add_view(id){
    $.ajax({
        type: "POST",
        url: '/add_view/'+id,
        success: success
    }).fail(function(e){
        alert("error - add_view");
    });
    
    function success(data){
        var views = data["views"];
        $("#goal_view_"+id).html(views+" Views");
        console.log(views)
    };
};

function add_like(id){
    $.ajax({
        type: "POST",
        url: '/add_like/'+id,
        success: success
    }).fail(function(e){
        alert("error - add_like");
    });
    
    function success(data){
        var likes = data["likes"];
        $("#goal_like_"+id).html(likes);
        console.log(likes)
    };
};

function follow(id){
    //alert(id);
    $.ajax({
        type: "POST",
        url: '/follow/'+id,
        success: success
    }).fail(function(e){
        alert("error - follow");
    });
    
    function success(data){
        if(data['following'] == 'yes'){
            $('.follow_user').addClass('hidden');
            $('.unfollow_user').removeClass('hidden');
        }
    };
};

function unfollow(id){
    $.ajax({
        type: "POST",
        url: '/unfollow/'+id,
        success: success
    }).fail(function(e){
        alert("error - follow");
    });
    
    function success(data){
        if(data['following'] == 'no'){
            $('.follow_user').removeClass('hidden');
            $('.unfollow_user').addClass('hidden');
        }
    };
};

function make_victory(id){
     NProgress.start();
    $.ajax({
        type: "POST",
        url: '/add_victory/'+id,
        success: success
    }).fail(function(e){
         NProgress.done();
        alert("error - ad_victory");
    });
    
    function success(data){
         NProgress.done();
        //$("#victories_achieved_count_modal").html(data["victories"]+" victories");
        $("#vic_img_url_goal_id").val(data["goal_id"]);
        $("#vic_congrats_goal_id").val(data["goal_id"]);
        $("#vid_goal_id").val(data["goal_id"]);
        
        $('#victoryModal').foundation('reveal', 'open');
    };
};

function get_upload_url(callback, img_type){
    
    var dfd = new jQuery.Deferred()
    
    $.ajax({
        type: "get",
        data: {"callback_url": callback, "img_type": img_type},
        url: "/get_upload_url",
        success: success
    }).fail(function(data){
        alert("FAIL");
        dfd.reject(data);
    });
    
    function success(data){

        var upload_url = data["upload_url"];
        
        dfd.resolve(upload_url);

    };
    
    return dfd.promise()
    
};

function check_file_size($file_input, max_size){//max_size in bytes
    if (window.File && window.FileReader && window.FileList && window.Blob){
        //get the file size and file type from file input field
        var fsize = $file_input[0].files[0].size;
        if(fsize>max_size){
            alert(fsize +" The file you've chosen is too big, please ensure its less than 500kb");
        }else{
            return true
        };
    }else{
        alert("Please upgrade your browser, because your current browser lacks some new features we need!");
    }
};

function youtube_parser(url){
    var regExp = /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#\&\?]*).*/;
    var match = url.match(regExp);
    if (match&&match[7].length==11){
        return match[7];
    }else{
        alert("bad URL");
    };
};

function load_more_goals(e){
    NProgress.start();
    
    function success(data){
            NProgress.done();
            $("#next_curs").remove();
            var elems = $(data);
            elems.css("visibility", "hidden");
            $("#goal_list").append( elems ).imagesLoaded( function() {
                if( $("#vision_view_toggle").hasClass("vision_view_toggle_off") ){
                    toggle_vision_to_list();
                };
                if( $("#victory_view_toggle").hasClass("victory_view_toggle_off") ){
                    toggle_victory_to_list();
                };
                elems.css("visibility", "visible");
                $("#goal_list").masonry( 'appended', elems );
            });
            $("#goal_list").removeClass("loading_content");
            ellipsis();
        };
    
    
    if( $("#next_curs").length && !$("#goal_list").hasClass("loading_content") ){
        if( $("#goal_list").hasClass("page_victories") ){
            var victory = "yes";
        }else{
            var victory = "no";
        };
        if( $("#goal_list").hasClass("page_goals") ){
            var goal = "yes";
        }else{
            var goal = "no";
        };
        $("#goal_list").addClass("loading_content");
        
        var for_user = $("#goal_list").data("user-id");
        
        var next_curs = $("#next_curs").data("cursor");
        $.ajax({
            type: "get",
            data: {"cursor": next_curs, "goal": goal, "victory": victory, "for_user": for_user},
            url: '/page_goals',
            success: success
        }).fail(function(e){
             NProgress.done();
            alert("error - load_more_goals");
        });
    }else{
        NProgress.done();
    };
};

function load_more_feed_goals(e){
     NProgress.start();
    
    function success(data){
        NProgress.done();
        $("#next_curs").remove();
        $("#feed_container_column").append(data);
        reload_masonry_layout();
        
        $("#feed_container_column").removeClass("loading_content");
        ellipsis();
        resize_feed_image();
        size_profile_img_container();
    };
    
    
    if( $("#next_curs").length && !$("#feed_container_column").hasClass("loading_content") ){
        $("#feed_container_column").addClass("loading_content");
        var next_curs = $("#next_curs").data("cursor");
        $.ajax({
            type: "get",
            data: {"cursor": next_curs},
            url: '/page_feed_goals',
            success: success
        }).fail(function(e){
            NProgress.done();
            alert("error - load_more_goals");
        });

    }else{
        NProgress.done();
    };
};

function reload_masonry_layout(){
    NProgress.start();
    var $container = $("#goal_list");
    $container.masonry('reloadItems')
    $container.imagesLoaded( function() {
        $container.masonry({
          itemSelector: '.item',
          "gutter": 10,
          "isFitWidth": true,
          columnWidth: ".item"
        });
        NProgress.done();
    });
};

/* ============= UTILITY FUNCTIONS ============================ */


/* ============= FACEBOOK ======================= */

  // You probably don't want to use globals, but this is just example code
  var fbAppId = '722137364473621';//'645800148788776';

  window.fbAsyncInit = function() {
    FB.init({
      appId      : fbAppId, // App ID
      status     : true,    // check login status
      cookie     : true,    // enable cookies to allow the
                            // server to access the session
      xfbml      : true     // parse page for xfbml or html5
                            // social plugins like login button below
    });

    $("body").on("click", ".invite_fb_friend", function(){
        //alert("send message");
        FB.ui({
            method: 'send',
            link: 'http://bucketvision.com',
            name: 'Bucket Vision',
            picture: 'http://bucketvision.com/static/images/bucketvision_title_white.png',
            caption: 'Bucket Vision',
            description: 'Join Bucket Vision, a place to share your Visions and Victories'
        });
        
    });
    
    };
    
  // Load the SDK Asynchronously
  (function(d, s, id){
     var js, fjs = d.getElementsByTagName(s)[0];
     if (d.getElementById(id)) {return;}
     js = d.createElement(s); js.id = id;
     js.src = "//connect.facebook.net/en_US/all.js";
     fjs.parentNode.insertBefore(js, fjs);
   }(document, 'script', 'facebook-jssdk'));

/* ============= END FACEBOOK ======================= */

