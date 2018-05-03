$(function () {

  // break caching
  var time = (new Date()).getTime();

  $.get("/static/data/tables/accessibility/domains.json?" + time, function(data) {
    var table = Tables.init(data.data, {
      columns: [
        {
          data: "domain",
          width: "210px",
          cellType: "th",
          createdCell: function (td) {td.scope = "row";}
        },
        {
          data: "errors",
          width: "60px",
        },
        {data: "agency"},
        {
          data: "errorlist",
          render: a11yErrorList
        }
      ]
    });


    /**
    * Make the row expand when any cell in it is clicked.
    *
    * DataTables' child row API doesn't appear to work, likely
    * because we're getting child rows through the Responsive
    * plugin, not directly. We can't put the click event on the
    * whole row, because then sending the click to the first cell
    * will cause a recursive loop and stack overflow.
    *
    * So, we put the click on every cell except the first one, and
    * send it to its sibling. The first cell is already wired.
    */
    $('table tbody').on('click', 'td:not(.sorting_1)', function(e) {
      $(this).siblings("th.sorting_1").click();
    });

    // TODO: move this to Tables.js.
    // Adds keyboard control to first cell of table
    Utils.detailsKeyboardCtrl();
    table.on("draw.dt",function(){
       Utils.detailsKeyboardCtrl();
    });

  });

  var a11yErrorList = function(data, type, row) {
    var errorListOutput = "";

    $.each(data, function(key, value) {
      if (value)
        errorListOutput += "<li><a href=\"/a11y/domain/" + row['domain'].replace(/http:\/\//i, '') + "#" + key.replace(/\s/g, '').replace(/\//i, '') + "\" target=\"_blank\">" + key + ": " + value + "</a></li>";
    });

    if (!errorListOutput)
      return "</hr><span class=\"noErrors\">No errors found.</span>";
    else
      return "</hr><ul class=\"errorList\">" + errorListOutput + "</ul></hr>";
  };

});
