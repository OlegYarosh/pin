// Generated by CoffeeScript 1.4.0
(function() {

  jQuery(function() {
    $("#add_new_admin_user_button").click(function() {
      window.location.href = '/admin/admin_user/';
    });
    $("#add_new_admin_permission_button").click(function() {
      window.location.href = '/admin/admin_rol/';
    });
    $("#admin_permission_list").on('click', '.delete', function() {
      $.permsid = $(this).attr('permsid');
      $.permsname = $(this).attr('permsname');
      $("#delete_confirmation_dialog_id").html($.permsid);
      $("#delete_confirmation_dialog_name").html($.permsname);
      $("#delete_confirmation_dialog").dialog('open');
    });
    $('#delete_confirmation_dialog').dialog({
      autoOpen: false,
      modal: true,
      buttons: {
        'Cancel': function() {
          $(this).dialog('close');
        },
        'Confirm delete': function() {
          var url;
          $.confirm_dialog = $(this);
          url = "/admin/admin_rol/" + $.permsid + "/";
          $.ajax(url, {
            type: 'DELETE',
            dataType: 'json',
            success: function(data) {
              $("#perm" + $.permsid).remove();
              $.confirm_dialog.dialog('close');
            }
          });
        }
      }
    });
  });

}).call(this);
