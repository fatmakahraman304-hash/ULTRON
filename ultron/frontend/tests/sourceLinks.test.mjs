import test from 'node:test';import assert from 'node:assert/strict';
import {sourceParts,sourceUrl,researchMeta,searchWidgetDocument} from '../src/dashboard/sourceLinks.ts';
test('real source links and markdown citations are clickable without executing HTML',()=>{
 const parts=sourceParts('Kaynak: [Rapor](https://example.org/report) ve https://example.org/price.');
 assert.deepEqual(parts.filter(x=>x.href).map(x=>x.href),['https://example.org/report','https://example.org/price']);
 assert.equal(parts.filter(x=>x.href)[0].text,'Rapor');
 assert.equal(sourceParts('<script>alert(1)</script>')[0].text,'<script>alert(1)</script>');
});
test('credentials, scripts and private addresses are not links',()=>{
 for(const url of ['javascript:alert(1)','file:///etc/passwd','http://127.0.0.1','https://user:pass@example.org','http://node.internal'])assert.equal(sourceUrl(url),null);
});
test('stored metadata and search suggestion iframe retain isolation',()=>{
 assert.equal(researchMeta('{"search_suggestions_html":"hello"}').search_suggestions_html,'hello');
 assert.equal(researchMeta('invalid'),undefined);
 assert.match(searchWidgetDocument('widget'),/default-src 'none'/);
 assert.match(searchWidgetDocument('widget'),/form-action 'none'/);
});
