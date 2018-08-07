$(document).ready(function(){

  $('.message .close')
  .on('click', function() {
    $(this)
      .closest('.message')
      .transition('fade');
  });

  // Used in manage workflows
  $('#context1 .menu .item')
    .tab({
      context: $('#context1')
    });

  $('#context2 .menu .item')
    .tab({
      // special keyword works same as above
      context: 'parent'
    });

  $('.progress').progress({
    percent: 22
  });

  $('.ui.checkbox').checkbox();

  $('.test.modal').modal('attach events', '.suite.details', 'show');

  $('.ui.accordion')
    .accordion();
});
