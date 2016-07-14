(function($){
  $(function(){

    $('.button-collapse').sideNav();

    $('.collapsible').collapsible();



    $('.datepicker').pickadate({
	    selectMonths: true, // Creates a dropdown to control month
	    selectYears: 15 // Creates a dropdown of 15 years to control year
  	});
  	$('select').material_select();

    // Medium Editor
    /*var elements = document.querySelectorAll('.editable'),
    editor = new MediumEditor(elements, {
    	paste: {
    		forcePlainText: false,
    	},
    	buttons: ['underline', 'anchor', 'header1', 'header2', 'quote', 'image'],
    	imageDragging: true
	});*/

	$("body").on("click", ".approve_blog", function(){
		var $this = $(this);
		var blog_id = $this.data("id");
		console.log(blog_id);
		if( $this.is(":checked") ){
			var approve_blog = true;
		}else{
			var approve_blog = false;
		};

		function success(data){
			if(data["message"] = "success"){
				console.log("approved blog");
			}else{
				alert("an error occurred");
			}
		};

		$.ajax({
			url: "/admin/approve_blog",
			type: 'post',
			data: {"blog_id": blog_id, "approve_blog": approve_blog},
			success: success
		}).fail(function(){
			alert("Ajax failed, an error occurred");
		});

	});

  }); // end of document ready
})(jQuery); // end of jQuery name space