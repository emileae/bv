(function($){
  $(function(){
    $('.tooltipped').tooltip({delay: 50});
    //$('.materialboxed').materialbox();// now override in gallery template, since its been modified on github
     $(".button-collapse").sideNav();

     // dropdown
     $(".dropdown-button").dropdown();

     // slider
     $('.slider').slider({full_width: true, interval: 6000});


  }); // end of document ready
})(jQuery); // end of jQuery name space

$(document).ready(function(){

	$(".page-tab").click(function() {
	    $('html, body').animate({
	        scrollTop: $(this).next(".row").offset().top - 64
	    }, 1000);
	});

  // image-map
  $('map').imageMapResize();

});