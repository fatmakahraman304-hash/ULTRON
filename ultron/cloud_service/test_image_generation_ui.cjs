const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(__dirname + '/static/index.html', 'utf8');
const inline = html.match(/<script>([\s\S]*?)<\/script>/);
if (!inline) throw new Error('inline chat script missing');
new vm.Script(inline[1]);
const start = inline[1].indexOf('function isImageCreationRequest');
const end = inline[1].indexOf('async function sendImageCreation', start);
if (start < 0 || end < 0) throw new Error('image intent handlers missing');
const context = { lastImageFile: null, GolgeImages: require('./static/image-intents.js') };
vm.runInNewContext(inline[1].slice(start, end), context);
for (const prompt of ['Resim oluştur', 'Bir kedi resmi çiz', 'Mavi bir daire oluştur', 'Create an image of a red car']) {
  if (!context.isImageCreationRequest(prompt)) throw new Error('image request was not recognized: ' + prompt);
}
if (context.isImageCreationRequest('2009 Mercedes C180 yakıt tüketimi?')) throw new Error('ordinary chat was captured as image creation');
if (!inline[1].includes("Görseli indir / kaydet")) throw new Error('generated image download action missing');
if (!inline[1].includes("'/api/image/generated/'+messageId")) throw new Error('owner-authenticated image route not used');
if (!inline[1].includes('function attachGeneratedImage(bubble,id)')) throw new Error('saved images are not restored on reload');
if (!inline[1].includes('has_generated_image:m.has_generated_image')) throw new Error('chat history drops image metadata');
if (!inline[1].includes('image_unavailable:m.image_unavailable')) throw new Error('expired images falsely remain available');
if (inline[1].includes('generatedImageUrls')) throw new Error('transient image blobs still used as sole storage');
context.lastImageFile = {};
if (!context.isImageCreationRequest('Daha iyi yap')) throw new Error('image improvement follow-up was not recognized');
if (!context.isImageFollowupRequest('Fotoğrafta ne yazıyor?')) throw new Error('image question follow-up was not recognized');
console.log('✔ image creation, editing and visible-image follow-up intents');
