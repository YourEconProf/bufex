import unittest
import pandas as pd
from BUFEX_subs import expand_transactions


class PrimesTestCase(unittest.TestCase):
    """Tests for `BUFEX_subs.py`."""
    
    def test_if_expand_transactions_works(self):
        """Can expand_transactions do a basic expansion?"""
        # create pandas df to pass in, along with correct expansion
        # df.in:
        #      Badge   Qty   Cmdty   Price
        # 0      4      1     BP1      10
        # 1      5      2     BP1      12
        # 2      4      3     BP1      10
        # df.out:
        #      Badge   Qty   Cmdty   Price
        # 0      4      1     BP1      10
        # 1      4      2     BP1      10
        # 2      4      3     BP1      10
        # 3      4      4     BP1      10
        # 4      5      1     BP1      12
        # 5      5      2     BP1      12
        df_input = pd.DataFrame(
            {   'Badge' : pd.Series([4,5,4], index=[0,1,2]),
                'Qty'   : pd.Series([1,2,3], index=[0,1,2]),
                'Cmdty' : pd.Series(['BP1','BP1','BP1'], index=[0,1,2]),
                'Price' : pd.Series([10,12,10], index=[0,1,2])} )
        df_output = pd.DataFrame(
            {   'Badge' : pd.Series([4,4,4,4,5,5], index=[0,1,2,3,4,5]),
                'Qty'   : pd.Series([1,2,3,4,1,2], index=[0,1,2,3,4,5]),
                'Cmdty' : pd.Series(['BP1','BP1','BP1','BP1','BP1','BP1'], index=[0,1,2,3,4,5]),
                'Price' : pd.Series([10,10,10,10,12,12], index=[0,1,2,3,4,5])} )
        df_output.sort_index(inplace=True)
        print (df_input)
        print (df_output)
        print (expand_transactions(df_input))
        self.assertEqual(expand_transactions(df_input),df_output)
        
if __name__ == '__main__':
    unittest.main()
