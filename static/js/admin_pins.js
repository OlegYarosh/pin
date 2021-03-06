// Generated by CoffeeScript 1.4.0

jQuery(function() {
  $('#search_button').on('click', function(event) {
    var search_data;
    event.preventDefault();
    search_data = {
      'pin_url': $('#pin_url').val(),
      'username': $('#username').val(),
      'name': $('#name').val(),
      'email': $('#email').val(),
      'category': $('#category').val()
    };
    $.ajax({
      data: search_data,
      url: '/admin/pins/search/set_search_criteria',
      success: function() {
        $.pagination_grid.g.load();
      }
    });
  });
  $('.datagrid').on('click', '.edit-pin', function(event) {
    var pinid;
    event.preventDefault();
    event.stopPropagation();
    pinid = $(this).attr('pinid');
    window.location.href = '/admin/pin/' + pinid;
  });
  $('#select_all_pins').on('click', function(event) {
    return $.pagination_grid.g.selectAll();
  });
  $('#unselect_all_pins').on('click', function(event) {
    return $.pagination_grid.g.unSelectAll();
  });
  $('#delete_selected_pins').on('click', function(event) {
    var ids, x, _i, _len, _ref;
    if (!confirm('Do you really want to delete these items?')) {
      return;
    }
    ids = '';
    _ref = $.pagination_grid.g.getSelectedRows();
    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
      x = _ref[_i];
      if (ids !== '') {
        ids += ',';
      }
      ids += $(x).attr('pinid');
    }
    console.log(ids);
    $.ajax({
      method: 'post',
      url: '/admin/pins/multiple_delete',
      data: {
        'ids': ids
      },
      success: function() {
        $.pagination_grid.g.load();
      }
    });
  });
  $('body').on('click', '#delete_pin_button', function(event) {
    var pinid;
    event.preventDefault();
    event.stopPropagation();
    pinid = $(this).attr('pinid');
    $.ajax({
      url: '/admin/pin/' + pinid,
      method: 'delete',
      success: function() {
        $.pagination_grid.g.load();
        $('#pin_edit_dialog').dialog('close');
      }
    });
  });
  $('body').on('click', '.edit_button', function(event) {
    var pinid;
    pinid = $(this).attr('pinid');
    $('#pin_edit_dialog').load('/admin/pin/' + pinid);
    $('#pin_edit_dialog').dialog('open');
  });
  $('body').on('submit', '#pin_edit_form', function(event) {
    $(this).ajaxSubmit({
      data: $(this).serialize(),
      success: function() {
        $('#pin_edit_dialog').dialog('close');
        $.pagination_grid.g.load();
        return false;
      }
    });
    return false;
  });
  $('#pin_edit_dialog').dialog({
    autoOpen: false,
    position: {
      my: "center top",
      at: "center top",
      of: window
    },
    height: 'auto',
    width: 1000
  });
});
