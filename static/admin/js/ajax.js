

// parameters: jquery form selector, like $(form), GET/POST, url, success callback function
function submit_form_ajax($form, method, action, success){

  var form = $form[0]; // You need to use standart javascript object here
  var formData = new FormData(form);

  var loader = $form.find(".loader-icon");
  var loader_success = $form.find(".loader-success");
  var loader_error = $form.find(".loader-error");
  // reset loaders
  if(!loader_success.hasClass("hide")){
    loader_success.addClass("hide");
  };
  if(!loader_error.hasClass("hide")){
    loader_error.addClass("hide");
  };

  loader.toggleClass("hide");

  function success_fn(data){
    loader.addClass("hide");
    loader_error.addClass("hide");
    loader_success.removeClass("hide");

    setTimeout(function(){
      loader_success.addClass("hide");
    }, 3000);

    success(data, $form);

  };

  $.ajax({
      url: action,
      type: method,
      data: formData,
      
      // THIS MUST BE DONE FOR FILE UPLOADING
      contentType: false,
      processData: false,
      
      success: success_fn
  }).fail(function(){
    loader.addClass("hide");
    loader_error.removeClass("hide");
    loader_success.addClass("hide");
  });

};



$("body").on('submit', '.ajax-form-content', function(e){
  e.preventDefault();

  function success(data, $form){
    console.log("ajax upload success")
  };

  var method = $(this).attr("method");
  var action = $(this).attr("action");

  submit_form_ajax( 
    $(this), 
    method, 
    action, 
    success
    );
});

$("body").on('submit', '.ajax-form-image-gallery', function(e){
  e.preventDefault();

  var $this = $(this);

  var success = function success(data, $form){
    console.log("ID: .... ", data["gallery_image_id"])
    console.log("ajax gallery image upload success");

    $form.attr( "id", "gallery_image_"+data["gallery_image_id"] );
    $form.find(".preview-image-container").append("<img src='"+data["gallery_image_url"]+"' class='preview-image'>")

  };

  var method = $this.attr("method");
  var action = $this.attr("action");

  submit_form_ajax( 
    $this, 
    method, 
    action, 
    success
    );
});
