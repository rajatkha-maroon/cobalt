#include <bits/stdc++.h>

using namespace std;

int main(void)
{
	vector<int> values = {0,1,2,3,4,5,6,7,10,11,12,13,14,15,16,17,20,21,22,23,24,25,26,27,30,31,32,33,34,35,36,37,40,41,42,43,44,45,46,47,50,51,52,53,54,55,56,57};

	int r = 0;
	int l = 0;
	int size;

	cout << "<BG>" << endl;
	cout << "<PartitionList>" << endl;

	while (r < 48) {
		printf("   <Partition name='ANL-R%.2d-1024'>\n", values[r]);
		for (int i = 0; i < 2; i++) {
			for (int j = 0; j < 16; j++)
				printf("      <NodeCard id='R%.2d-M%d-N%.2d' />\n", values[r], i, j);
		}
		cout << "   </Partition>" << endl;

		for (int i = 0; i < 2; i++) {
			printf("   <Partition name='ANL-R%.2d-M%d-512'>\n", values[r], i);
                        for (int j = 0; j < 16; j++)
				printf("      <NodeCard id='R%.2d-M%d-N%.2d' />\n", values[r], i, j);

			cout << "   </Partition>" << endl;
		}

		l = r - 1;
		while (l >= 0) {
			size = ((r - l) + 1) * 1024;
			printf("   <Partition name='ANL-R%.2d-R%.2d-%d'>\n", values[l], values[r], size);

			for (int i = l; i <= r; i++) {
				for (int j = 0; j < 2; j++) {
		                        for (int k = 0; k < 16; k++)
		                                printf("      <NodeCard id='R%.2d-M%d-N%.2d' />\n", values[i], j, k);
		                }
			}

			cout << "   </Partition>" << endl;

			l--;
		}

		r++;
	}

	cout << "</PartitionList>" << endl;
	cout << "</BG>" << endl;
}
