$(document).ready(function () {

  $.get("/data/organizations/https.json", function(data) {

    Tables.initAgency(data.data, {

      csv: "/data/hosts/https.csv",

      columns: [
        {
          className: 'control',
          orderable: false,
          data: "",
          render: Tables.noop,
          visible: false
        },
        {
          data: "name_" + getLanguage(),
          cellType: "td",
          render: eligibleHttps,
          createdCell: function (td) {td.scope = "row";}
        },
        {
          data: "https.enforces",
          render: Tables.percent("https", "enforces")
        },
        {
          data: "https.hsts",
          render: Tables.percent("https", "hsts")
        },
        {
          data: "crypto.bod_crypto",
          render: Tables.percent("crypto", "bod_crypto")
        },
        {
          data: "preloading.preloaded",
          render: Tables.percent("preloading", "preloaded")
        },
      ]

    });
  });

  var getLanguage = function() {
    var prefix = $( "#data_table" ).attr("language");
    if(prefix == 'en' || prefix == 'fr') return prefix;
    else return 'en';
  }

  var eligibleHttps = function(data, type, row) {
    var services = row.https.eligible;
    var domains = row.total_domains;
    var language = getLanguage();

    if(language == 'en') 
      var name = row.name_en;
    else
      var name = row.name_fr;

    var services_text = "service";
    if (type == "sort") return name;

    if(services > 1) 
      services_text = "services"

    var link = function(text) {
      return "" +
        "<a href=\"/en/domains/#" +
          QueryString.stringify({q: row["name_en"]}) + "\">" +
           text +
        "</a>";
    }

    return "<div class=\"mb-2\">" + name + "</div>" + link("Show " + services + " " + services_text);

  };


});
