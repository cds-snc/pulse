$(function(){

  var KEYCODE_ESC = 27;

  $('#menu-btn, .overlay, .sliding-panel-close').on('click touchstart',function (e) {
    $('#menu-content, .overlay').toggleClass('is-visible');

    if($('#menu-content').hasClass('is-visible')) {
      $('#menu-content a').attr('tabindex', '0');
    }
    else {
      $('#menu-content a').attr('tabindex', '-1');
    }

    e.preventDefault();
  });

  $('#modal-btn').on('click touchstart', function (e) {
    $('#modal').toggleClass('hidden flex');

    e.preventDefault();
  });

  $('#close-btn').on('click touchstart', function (e) {
    $('#modal').toggleClass('hidden flex');

    e.preventDefault();
  });

  $(document).keyup(function(e) {
    if(e.keyCode === KEYCODE_ESC) {
      if($('#modal').hasClass('flex')) $('#modal').toggleClass('hidden flex');
    };
  })

});
